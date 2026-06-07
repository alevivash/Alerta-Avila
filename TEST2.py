import ee
import json
import requests
from PIL import Image
from io import BytesIO

# 1. Inicializar GEE con tu proyecto
ee.Initialize(project='alertas-temprana-avila')

# =====================================================================
# FUNCIÓN NUEVA: MÁSCARA DE NUBES PARA SENTINEL-2
# =====================================================================
def mask_s2_clouds(image):
    """
    Usa la banda QA60 para enmascarar (borrar) nubes densas y cirrus.
    """
    qa = image.select('QA60')
    # Los bits 10 y 11 son nubes y cirrus, respectivamente.
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11
    # Ambos flags deben estar en 0 (indicando cielo despejado).
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
    return image.updateMask(mask)

# =====================================================================
# 2. CARGAR EL POLÍGONO REAL DEL ÁVILA DESDE GEOJSON LOCAL
# =====================================================================
geojson_path = 'el_avila_waraira_repano.geojson'  # Ajusta la ruta si es necesario

with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

# Extraer la geometría del GeoJSON
if geojson_data['type'] == 'FeatureCollection':
    geom_dict = geojson_data['features'][0]['geometry']
elif geojson_data['type'] == 'Feature':
    geom_dict = geojson_data['geometry']
else:
    geom_dict = geojson_data

# Convertir a geometría de Earth Engine
roi = ee.Geometry(geom_dict)

area_km2 = roi.area().getInfo() / 1e6
print(f"✅ Polígono cargado desde {geojson_path}. Área: {area_km2:.2f} km²")
if area_km2 <= 0:
    print("⚠️ El polígono parece vacío o mal proyectado. Revisa el archivo.")
    exit()

# =====================================================================
# 3. BUSCAR IMÁGENES Y APLICAR MEDIANA SIN NUBES
# =====================================================================

# Filtro temporal
sentinel_coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate('2026-02-01', '2026-03-25')
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) # Relajamos un poco porque la máscara hará el trabajo sucio
                      .sort('system:time_start', False))

conteo = sentinel_coleccion.size().getInfo()
print(f"Imágenes base encontradas: {conteo}")

if conteo > 0:
    # Obtener la fecha de la imagen más reciente para calcular el histórico
    imagen_referencia = sentinel_coleccion.first()
    fecha_actual = ee.Date(imagen_referencia.get('system:time_start'))
    
    # NUEVO: Aplicar máscara de nubes y calcular la MEDIANA para tener un mapa 100% despejado
    imagen_actual_limpia = sentinel_coleccion.map(mask_s2_clouds).median()
    
    # Calcular NDVI de la imagen compuesta limpia
    ndvi_actual = imagen_actual_limpia.normalizedDifference(['B8', 'B4']).rename('NDVI_actual')
    
# =====================================================================
    # 4. HISTÓRICO (AMPLIADO Y SIN FILTRO REESTRICTIVO DE NUBES)
    # =====================================================================
    # Ampliamos a 45 días hacia atrás para asegurar suficientes datos
    fecha_inicio_historico = fecha_actual.advance(-45, 'day')
    
    coleccion_historica = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                            .filterBounds(roi)
                            .filterDate(fecha_inicio_historico, fecha_actual)
                            # Eliminamos el .filter(lt('CLOUDY...')) y dejamos que la máscara haga el trabajo
                            .map(mask_s2_clouds)) 
    
    # Validamos que no esté vacía antes de hacer la matemática
    conteo_hist = coleccion_historica.size().getInfo()
    print(f"Imágenes históricas encontradas para promediar: {conteo_hist}")
    
    if conteo_hist > 0:
        # Calcular el NDVI histórico
        ndvi_historico_promedio = (coleccion_historica
                                   .map(lambda img: img.normalizedDifference(['B8', 'B4']))
                                   .median()
                                   .rename('NDVI_hist'))

        # =====================================================================
        # 5. CALCULAR DELTA NDVI Y RECORTAR AL ÁVILA
        # =====================================================================
        delta_ndvi = (ndvi_actual.subtract(ndvi_historico_promedio)
                      .divide(ndvi_historico_promedio)
                      .multiply(100)
                      .rename('Delta_NDVI'))
        
        delta_avila = delta_ndvi.clip(roi)
        
        print("\n¡Éxito en la Fase Analítica!")
        
        # =====================================================================
        # 6. DESCARGA DEL MAPA VISUAL
        # =====================================================================
        parametros_visuales = {
            'min': -30,
            'max': 0,
            'palette': ['red', 'yellow', 'green'],
            'dimensions': 800,
            'region': roi,
            'format': 'png'
        }
        
        print("Descargando mapa de alertas sin nubes...")
        url_mapa = delta_avila.getThumbURL(parametros_visuales)
        
        respuesta = requests.get(url_mapa)
        if respuesta.status_code == 200:
            imagen_pil = Image.open(BytesIO(respuesta.content))
            imagen_pil.save("alerta_avila.png")
            print("👉 ¡Éxito! Archivo 'alerta_avila.png' actualizado.")
        else:
            print(f"❌ Error al descargar la imagen: {respuesta.status_code}")
    else:
        print("\n❌ Error: La colección histórica está vacía. Intenta ampliar el rango de días en 'advance'.")

else:
    print("\n⚠️ No se encontraron imágenes base en ese rango temporal.")
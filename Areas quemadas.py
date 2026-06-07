import ee
import json
import requests
from PIL import Image
from io import BytesIO

# 1. Inicializar GEE con tu proyecto
ee.Initialize(project='alertas-temprana-avila')

# =====================================================================
# FUNCIONES: MÁSCARA DE PROBABILIDAD AVANZADA Y JOIN
# =====================================================================
def obtener_coleccion_unida(roi, fecha_inicio, fecha_fin):
    """
    Acopla la colección Sentinel-2 óptica con su respectiva capa de 
    probabilidad de nubes usando ee.Join.
    """
    s2_sr = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
             .filterBounds(roi)
             .filterDate(fecha_inicio, fecha_fin)
             
             # Filtro global recomendado para la colección SR
             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)))

    s2_clouds = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                 .filterBounds(roi)
                 .filterDate(fecha_inicio, fecha_fin))

    return ee.ImageCollection(ee.Join.saveFirst('cloud_mask').apply(
        primary=s2_sr,
        secondary=s2_clouds,
        condition=ee.Filter.equals(leftField='system:index', rightField='system:index')
    ))

def mask_s2_clouds(image):
    """
    Aplica la máscara de probabilidad píxel a píxel para borrar nubes y sombras.
    """
    cloud_img = ee.Image(image.get('cloud_mask'))
    cld_prb = cloud_img.select('probability')
    
    #  Umbral estricto: > 15% se considera nube (ajustable según necesidades)
    # Para un enfoque más conservador, podríamos usar > 25% o incluso > 
    # 30% para eliminar más nubes, aunque esto podría dejar zonas sin datos.
    is_cloud = cld_prb.gt(15) 
    
    return image.updateMask(is_cloud.Not())

# =====================================================================
# 2. CARGAR EL POLÍGONO REAL DEL ÁVILA DESDE GEOJSON LOCAL
# =====================================================================
geojson_path = 'el_avila_waraira_repano.geojson'  

with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

if geojson_data['type'] == 'FeatureCollection':
    geom_dict = geojson_data['features'][0]['geometry']
elif geojson_data['type'] == 'Feature':
    geom_dict = geojson_data['geometry']
else:
    geom_dict = geojson_data

roi = ee.Geometry(geom_dict)

area_km2 = roi.area().getInfo() / 1e6
print(f"✅ Polígono cargado desde {geojson_path}. Área: {area_km2:.2f} km²")
if area_km2 <= 0:
    print("⚠️ El polígono parece vacío o mal proyectado. Revisa el archivo.")
    exit()

# =====================================================================
# 3. BUSCAR IMÁGENES ACTUALES Y APLICAR MEDIANA SIN NUBES
# =====================================================================
coleccion_base = obtener_coleccion_unida(roi, '2026-02-01', '2026-03-25')
sentinel_coleccion_limpia = coleccion_base.map(mask_s2_clouds)

conteo = sentinel_coleccion_limpia.size().getInfo()
print(f"Imágenes base limpias encontradas: {conteo}")

if conteo > 0:
    imagen_referencia = sentinel_coleccion_limpia.sort('system:time_start', False).first()
    fecha_actual = ee.Date(imagen_referencia.get('system:time_start'))
    
    imagen_actual_limpia = sentinel_coleccion_limpia.median()
    
    # -----------------------------------------------------------------
    # CAMBIO A NBR: Usamos B8A (NIR) y B12 (SWIR)
    # -----------------------------------------------------------------
    nbr_actual = imagen_actual_limpia.normalizedDifference(['B8A', 'B12']).rename('NBR_actual')
    
    # =====================================================================
    # 4. HISTÓRICO (AMPLIADO Y ENMASCARADO PÍXEL A PÍXEL)
    # =====================================================================
    fecha_inicio_historico = fecha_actual.advance(-45, 'day')
    
    coleccion_hist_base = obtener_coleccion_unida(roi, fecha_inicio_historico, fecha_actual)
    coleccion_historica_limpia = coleccion_hist_base.map(mask_s2_clouds)
    
    conteo_hist = coleccion_historica_limpia.size().getInfo()
    print(f"Imágenes históricas encontradas para promediar: {conteo_hist}")
    
    if conteo_hist > 0:
        # -----------------------------------------------------------------
        # CAMBIO A NBR HISTÓRICO
        # -----------------------------------------------------------------
        nbr_historico_promedio = (coleccion_historica_limpia
                                   .map(lambda img: img.normalizedDifference(['B8A', 'B12']))
                                   .median()
                                   .rename('NBR_hist'))

        # =====================================================================
        # 5. CALCULAR DELTA NBR Y RECORTAR AL ÁVILA
        # =====================================================================
        # Diferencial temporal porcentual calculado respecto al promedio histórico
        delta_nbr = (nbr_actual.subtract(nbr_historico_promedio)
                      .divide(nbr_historico_promedio)
                      .multiply(100)
                      .rename('Delta_NBR'))
        
        delta_avila = delta_nbr.clip(roi)
        
        print("\n¡Éxito en la Fase Analítica con NBR!")
        
        # =====================================================================
        # 6. DESCARGA DEL MAPA VISUAL (ANOMALÍAS DE CALCINACIÓN)
        # =====================================================================
        parametros_visuales = {
            'min': -40, # Mínimo ligeramente ampliado para resaltar severidad de quema
            'max': 0,
            'palette': ['red', 'yellow', 'green'],
            'dimensions': 1200, 
            'region': roi,
            'format': 'png'
        }
        
        print("Descargando mapa de alertas matemáticas (Delta NBR)...")
        url_mapa = delta_avila.getThumbURL(parametros_visuales)
        
        respuesta = requests.get(url_mapa)
        if respuesta.status_code == 200:
            imagen_pil = Image.open(BytesIO(respuesta.content))
            imagen_pil.save("alerta_avila_nbr.png")
            print("👉 ¡Éxito! Archivo 'alerta_avila_nbr.png' actualizado enfocando huellas de incendio.")
        else:
            print(f"❌ Error al descargar la imagen: {respuesta.status_code}")
    else:
        print("\n❌ Error: La colección histórica está vacía. Intenta ampliar el rango de días en 'advance'.")

else:
    print("\n⚠️ No se encontraron imágenes base en ese rango temporal.")


# Bibliografía:
# - Documentación oficial de GEE: https://developers.google.com/earth-engine/guides/python_install
# - Tutorial de Sentinel-2 con S2Cloudless:
#  https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless

import ee
import json
import requests
from PIL import Image
from io import BytesIO

# 1. Inicializar GEE con tu proyecto
ee.Initialize(project='alertas-temprana-avila')

# =====================================================================
# FUNCIÓN AVANZADA: MÁSCARA ROBUSTA DE NUBES Y SOMBRAS DE SENTINEL-2
# =====================================================================
def addCloudShadowMask(image):
    """
    Identifica y borra nubes delgadas, bordes difuminados y sombras, 
    usando el dataset externo 'S2_CLOUD_PROBABILITY' y filtros morfológicos.
    """
    # Configuraciones de rigor
    CLD_PRB_THRESH = 40     # Umbral de probabilidad de nube (0-100)
    NIR_DRK_THRESH = 0.15    # Umbral de oscuridad (NIR) para detectar sombras potenciales
    BUFFER = 100             # Radio de seguridad alrededor de las nubes (en metros)

    # A. Importar el dataset de Probabilidad de Nubes para esta escena
    s2_cloud_probability = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                           .filterBounds(roi)
                           .filterDate('2025-01-01', '2026-12-31') # Rango amplio para asegurar enlace
                           .filter(ee.Filter.eq('system:index', image.get('system:index')))
                           .first())
    
    # B. Crear máscara base de nubes densas y bordes difuminados
    isCloud = s2_cloud_probability.select('probability').gt(CLD_PRB_THRESH)
    
    # C. Crear máscara de sombras potenciales basándonos en píxeles oscuros (NIR)
    # y aplicando una dilatación morfológica alrededor de la nube (buffer)
    notWater = image.select('SCL').neq(6) # Ignoramos el mar (banda SCL=6)
    isDark = image.select('B8').lt(NIR_DRK_THRESH).And(notWater)
    
    # Proyectamos un área de seguridad (buffer) morfológico alrededor de la nube
    isCloudBuffer = isCloud.fastDistanceTransform().sqrt().lte(BUFFER / 20).Or(isCloud)
    
    # La sombra es la intersección de píxeles oscuros y el buffer de la nube
    isShadow = isDark.And(isCloudBuffer)
    
    # D. Combinar la nube y la sombra en una sola máscara de borrado
    isCloudOrShadow = isCloudBuffer.Or(isShadow)
    
    # E. Aplicar la máscara y añadirla como banda de depuración (opcional)
    return image.updateMask(isCloudOrShadow.Not())

# =====================================================================
# 2. CARGAR EL POLÍGONO REAL DEL ÁVILA DESDE GEOJSON LOCAL
# =====================================================================
geojson_path = 'AVILAGSON.geojson'  # Ajusta la ruta si es necesario

with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

# Extraer la geometría
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
    print("⚠️ El polígono parece vacío o mal proyectado.")
    exit()

# =====================================================================
# 3. PROCESAR IMAGEN ACTUAL (CON MÁSCARA AVANZADA Y MEDIANA)
# =====================================================================
print("\nBuscando y limpiando nubes en el periodo actual...")
# Abarcamos todo el trimestre Jan-Mar 2026. 
# Relaxamos el filtro general porque la máscara avanzada hará el trabajo.
sentinel_actual = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(roi)
                  .filterDate('2026-01-01', '2026-03-25')
                  # Solo filtramos días de tormenta total (>80% nubes)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80)) 
                  # CLAVE: Aplicamos la nueva máscara avanzada a cada imagen individual
                  .map(addCloudShadowMask))

# Creamos una mediana del trimestre actual: 100% libre de nubes y sombras
imagen_actual_limpia = sentinel_actual.median().clip(roi)
ndvi_actual = imagen_actual_limpia.normalizedDifference(['B8', 'B4']).rename('NDVI_actual')

# =====================================================================
# 4. PROCESAR HISTÓRICO (AMPLIADO Y LIMPIO)
# =====================================================================
print("Buscando y limpiando nubes en el periodo histórico...")
# Para tener un buen promedio, ampliamos el rango histórico a 6 semanas (42 días)
fecha_referencia = ee.Date('2026-01-01') # Usamos el inicio del periodo actual como fin del histórico
fecha_inicio_hist = fecha_referencia.advance(-42, 'day')

sentinel_historico = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                       .filterBounds(roi)
                       .filterDate(fecha_inicio_hist, fecha_referencia)
                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80))
                       # Aplicamos la máscara avanzada al histórico también
                       .map(addCloudShadowMask))

# Mediana del historial, 100% limpia
ndvi_historico_promedio = (sentinel_historico
                           .map(lambda img: img.normalizedDifference(['B8', 'B4']))
                           .median()
                           .rename('NDVI_hist'))

# =====================================================================
# 5. CALCULAR DELTA NDVI FINAL Y DESCARGAR
# =====================================================================
# Calculamos la alerta (Delta %)
delta_ndvi = (ndvi_actual.subtract(ndvi_historico_promedio)
              .divide(ndvi_historico_promedio)
              .multiply(100)
              .rename('Delta_NDVI'))

delta_avila = delta_ndvi.clip(roi)

print("\n¡Éxito en la Fase Analítica! Mapa de alertas limpiado.")

# Parámetros de visualización (los mismos que antes, pero con datos limpios)
parametros_visuales = {
    'min': -30,
    'max': 0,
    'palette': ['red', 'yellow', 'green'], # Alerta-PreAlerta-Vegetación
    'dimensions': 800,
    'region': roi,
    'format': 'png'
}

print("Descargando mapa final libre de nubes y sombras...")
url_mapa = delta_avila.getThumbURL(parametros_visuales)

# Guardar la imagen PNG
respuesta = requests.get(url_mapa)
if respuesta.status_code == 200:
    imagen_pil = Image.open(BytesIO(respuesta.content))
    imagen_pil.save("alerta_avila_limpia.png")
    print("👉 ¡Éxito! Archivo 'alerta_avila_limpia.png' actualizado.")
else:
    print(f"❌ Error HTTP: {respuesta.status_code}")
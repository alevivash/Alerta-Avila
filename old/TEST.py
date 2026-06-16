import ee
import requests
from PIL import Image
from io import BytesIO

# 1. Inicializar usando el ID del Proyecto de Cloud
ee.Initialize(project='alertas-temprana-avila')

# 2. Definir la ROI (El Ávila)
coordenadas_avila = [
    [-66.98, 10.55],
    [-66.70, 10.55],
    [-66.70, 10.48],
    [-66.98, 10.48],
    [-66.98, 10.55]
]
roi = ee.Geometry.Polygon([coordenadas_avila])

# ========================================================
# SEMANA 2: ADQUISICIÓN, DELTA HISTÓRICO Y EXPORTACIÓN LOCAL
# ========================================================

# 3. Filtros de búsqueda para la imagen actual
sentinel_coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate('2026-04-01', '2026-06-04')
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
                      .sort('system:time_start', False))

conteo = sentinel_coleccion.size().getInfo()
print(f"Imágenes encontradas que cumplen el criterio: {conteo}")

if conteo > 0:
    # 4. Seleccionar la imagen más reciente (Esta semana) y calcular su NDVI
    imagen_actual = sentinel_coleccion.first()
    ndvi_actual = imagen_actual.normalizedDifference(['B8', 'B4']).rename('NDVI_actual')
    
    # 5. Obtener dinámicamente las 3 semanas anteriores para el promedio histórico
    fecha_actual = ee.Date(imagen_actual.get('system:time_start'))
    fecha_inicio_historico = fecha_actual.advance(-21, 'day') # 21 días atrás
    
    coleccion_historica = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                            .filterBounds(roi)
                            .filterDate(fecha_inicio_historico, fecha_actual)
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60)))
    
    # Reducir la colección histórica mapeando el NDVI y calculando la media píxel por píxel
    ndvi_historico_promedio = (coleccion_historica
                               .map(lambda img: img.normalizedDifference(['B8', 'B4']))
                               .mean()
                               .rename('NDVI_hist'))

    # 6. Calcular el diferencial porcentual (Delta %) 
    # Fórmula: ((NDVI_actual - NDVI_hist) / NDVI_hist) * 100
    delta_ndvi = (ndvi_actual.subtract(ndvi_historico_promedio)
                  .divide(ndvi_historico_promedio)
                  .multiply(100)
                  .rename('Delta_NDVI'))
    
    delta_avila = delta_ndvi.clip(roi)
    
    # 7. Extraer ID y confirmar Fase Analítica
    id_imagen = imagen_actual.get('system:index').getInfo()
    print("\n¡Éxito en la Fase Analítica!")
    print(f"ID de la imagen Sentinel-2 procesada: {id_imagen}")
    
    # 8. Parámetros de visualización y descarga del mapa
    # Las caídas drásticas de NDVI (< -25%) se pintarán de rojo (Anomalía/Quema)
    parametros_visuales = {
        'min': -30,
        'max': 0,
        'palette': ['red', 'yellow', 'green'], 
        'dimensions': 800, 
        'region': roi
    }
    
    print("Descargando mapa visual desde los servidores de Google...")
    url_mapa = delta_avila.getThumbURL(parametros_visuales)
    
    # 9. Petición HTTP para traer los bytes de la imagen y guardarla localmente como PNG
    respuesta = requests.get(url_mapa)
    imagen_pil = Image.open(BytesIO(respuesta.content))
    imagen_pil.save("alerta_avila.png")
    
    print("👉 ¡Éxito! Archivo 'alerta_avila.png' guardado en tu carpeta de trabajo.")
else:
    print("\n⚠️ Alerta: No se encontraron imágenes Sentinel-2 en este rango de fechas con esa claridad.")
    print("Prueba ampliando el rango de fechas en el código.")
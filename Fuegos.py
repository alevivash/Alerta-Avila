import ee
import json
import requests
from PIL import Image
from io import BytesIO

# Inicializar GEE
ee.Initialize(project='alertas-temprana-avila')

# ====================================================
# FUNCIÓN NUEVA: MÁSCARA DE NUBES PARA SENTINEL-2
# ====================================================
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

# ====================================================
# 1. CARGAR EL POLÍGONO DESDE GEOJSON LOCAL
# ====================================================
with open('el_avila_waraira_repano.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

# Extraer la geometría (asume FeatureCollection o Geometry directa)
if geojson['type'] == 'FeatureCollection':
    geom = geojson['features'][0]['geometry']
elif geojson['type'] == 'Feature':
    geom = geojson['geometry']
else:
    geom = geojson

# Convertir a geometría de Earth Engine
roi = ee.Geometry(geom)

# Verificar que se cargó correctamente
area_km2 = roi.area().getInfo() / 1e6
print(f"✅ Polígono cargado. Área: {area_km2:.2f} km²")

# ====================================================
# 2. BUSCAR IMAGEN SATELITAL (Sentinel-2)
# ====================================================
# Aplicamos un filtro suave (ej. 60%) para descartar días de tormenta total, 
# pero confiamos en la máscara (.map) para limpiar el resto.
coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
             .filterBounds(roi)
             .filterDate('2026-01-01', '2026-03-25')
             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
             .map(mask_s2_clouds)) # <--- AQUÍ SE BORRAN LAS NUBES

n_imagenes = coleccion.size().getInfo()
print(f"Imágenes base encontradas para procesar: {n_imagenes}")

if n_imagenes == 0:
    print("❌ No se encontraron imágenes. Revisa las fechas o usa Landsat.")
    exit()

# Sacamos la primera imagen SOLO para extraer la fecha de referencia
imagen_base = coleccion.first()
fecha = ee.Date(imagen_base.get('system:time_start')).format('YYYY-MM-dd').getInfo()
print(f"📅 Fecha de referencia más reciente: {fecha}")

# Creamos un mosaic de imagenes
# y recortamos (.clip) la silueta exacta del parque
imagen = coleccion.mosaic().clip(roi) #Usamos mosaic de imagenes 


# ====================================================
# 3. GENERAR THUMBNAIL (color real)
# ====================================================
parametros = {
    'bands': ['B4', 'B3', 'B2'],
    'min': 0,
    'max': 2500,
    'scale': 20,          # resolución 20 m/píxel (equilibrio entre calidad y peso)
    'region': roi,
    'format': 'png'
}

print("Generando thumbnail del parque a color real y sin nubes...")
url = imagen.getThumbURL(parametros)
resp = requests.get(url, timeout=60)

if resp.status_code == 200:
    img = Image.open(BytesIO(resp.content))
    img.save("avila_color_real.png")
    print("✅ Imagen guardada exitosamente: avila_color_real.png")
    print(f"Tamaño: {img.size[0]} x {img.size[1]} píxeles")
else:
    print(f"❌ Error HTTP {resp.status_code}")
    print("Copia esta URL en el navegador para depurar:")
    print(url)
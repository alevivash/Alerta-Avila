# Sistema de Alerta Temprana para Incendios Forestales en el Waraira Repano
# Este script se encarga de generar un mapa a color real del Parque Nacional El Ávila (Waraira Repano) utilizando imágenes Sentinel-2, aplicando un filtro de nubes basado en la probabilidad de nubes y guardando el resultado localmente como PNG.
# Autor: [Alejandro Vivas]

import ee
import json
import requests
from PIL import Image
from io import BytesIO
import datetime

# Inicializar GEE
ee.Initialize(project='alertas-temprana-avila')

# ====================================================
# 1. CARGAR EL POLÍGONO DESDE GEOJSON LOCAL
# ====================================================
with open('el_avila_waraira_repano.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

if geojson['type'] == 'FeatureCollection':
    geom = geojson['features'][0]['geometry']
elif geojson['type'] == 'Feature':
    geom = geojson['geometry']
else:
    geom = geojson

roi = ee.Geometry(geom)
area_km2 = roi.area().getInfo() / 1e6
print(f"✅ Polígono cargado. Área: {area_km2:.2f} km²")

# ====================================================
# 2. CONFIGURAR LAS COLECCIONES DE IMÁGENES
# ====================================================
END_DATE = datetime.datetime.now()
START_DATE = END_DATE  - datetime.timedelta(days=45)  # Últimos 45 días 

# Colección 1: Imágenes de superficie (SR) con filtro global RECOMENDADO (50%)
s2_sr = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
         .filterBounds(roi)
         .filterDate(START_DATE, END_DATE)
         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))) 

# Colección 2: Probabilidad de nubes correspondiente
s2_clouds = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
             .filterBounds(roi)
             .filterDate(START_DATE, END_DATE))

# Unir las colecciones basándonos en el ID del sistema para poder usar la probabilidad
s2_sr_with_clouds = ee.ImageCollection(ee.Join.saveFirst('cloud_mask').apply(
    primary=s2_sr,
    secondary=s2_clouds,
    condition=ee.Filter.equals(leftField='system:index', rightField='system:index')
))

# ====================================================
# FUNCIÓN DE ENMASCARADO OPTIMIZADA, USANDO LA IMAGEN DE PROBABILIDAD. La desventaja es que elimina mas pixeles, puediendo dejar zonas sin datos, pero la ventaja es que es mucho más precisa para eliminar nubes y sombras.
# ====================================================
def mask_s2_clouds(image):
    # Extraer la imagen de probabilidad acoplada en el Join
    cloud_img = ee.Image(image.get('cloud_mask'))
    cld_prb = cloud_img.select('probability')
    
   
    # Para un enfoque más conservador, podríamos usar > 25% o incluso > 30%
    is_cloud = cld_prb.gt(25)   
    
    # Aplicar la máscara (oculta las nubes)
    return image.updateMask(is_cloud.Not())

# Aplicar la máscara a la colección acoplada
coleccion_limpia = s2_sr_with_clouds.map(mask_s2_clouds)

n_imagenes = coleccion_limpia.size().getInfo()
print(f"Imágenes base encontradas para procesar: {n_imagenes}")

if n_imagenes == 0:
    print("❌ No se encontraron imágenes limpias en este rango.")
    exit()

# Extraer fecha de referencia de la más reciente
imagen_base = coleccion_limpia.sort('system:time_start', False).first()
fecha = ee.Date(imagen_base.get('system:time_start')).format('YYYY-MM-dd').getInfo()
print(f" Fecha de referencia más reciente: {fecha}")

# Calcular la MEDIANA (el mejor reductor para series de tiempo)
imagen_final = coleccion_limpia.median().clip(roi)

# ====================================================
# 3. GENERAR THUMBNAIL (color real)
# ====================================================
parametros = {
    'bands': ['B4', 'B3', 'B2'],
    'min': 0,
    'max': 2500, # Bajamos un poco para ganar contraste en la vegetación oscura
    'scale': 20, 
    'region': roi,
    'format': 'png'
}

print("Generando thumbnail del parque a color real y sin nubes...")
url = imagen_final.getThumbURL(parametros)
resp = requests.get(url, timeout=60)

if resp.status_code == 200:
    img = Image.open(BytesIO(resp.content))
    img.save("avila_color_real.png")
    print("✅ Imagen guardada exitosamente: avila_color_real.png")
    print(f"Tamaño: {img.size[0]} x {img.size[1]} píxeles")
else:
    print(f"❌ Error HTTP {resp.status_code}")
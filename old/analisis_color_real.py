# Sistema de Alerta Temprana para Incendios Forestales en el Waraira Repano
# Este script se encarga de generar un mapa a color real del Parque Nacional El Ávila (Waraira Repano) utilizando imágenes Sentinel-2, aplicando un filtro de nubes basado en la probabilidad de nubes y guardando el resultado localmente como PNG.
# VERSION VIEJA
# Autor: [Alejandro Vivas]

import ee
import json
import requests
from PIL import Image
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import datetime as date

def descargar_mapa_preventivo(roi):
    """Genera un mapa a color real del Ávila usando S2_CLOUD_PROBABILITY con fechas dinámicas."""
    print("🛰️ Generando mapa satelital diario a color real (filtro avanzado de nubes)...")
    try:

        # Fechas dinámicas: Últimos 45 días para asegurar imágenes recientes, se actualizan cada día automáticamente. Se formatean como strings para evitar problemas de formato con GEE
        END_DATE = date.datetime.now().strftime('%Y-%m-%d')
        START_DATE = (date.datetime.now() - date.timedelta(days=45)).strftime('%Y-%m-%d')

        s2_sr = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                 .filterBounds(roi)
                 .filterDate(START_DATE, END_DATE)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)))

        s2_clouds = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                     .filterBounds(roi)
                     .filterDate(START_DATE, END_DATE))

        s2_sr_with_clouds = ee.ImageCollection(ee.Join.saveFirst('cloud_mask').apply(
            primary=s2_sr,
            secondary=s2_clouds,
            condition=ee.Filter.equals(leftField='system:index', rightField='system:index')
        ))

        def mask_s2_clouds(image):
            cloud_img = ee.Image(image.get('cloud_mask'))
            cld_prb = cloud_img.select('probability')
            is_cloud = cld_prb.gt(15)   
            return image.updateMask(is_cloud.Not())

        coleccion_limpia = s2_sr_with_clouds.map(mask_s2_clouds)

        n_imagenes = coleccion_limpia.size().getInfo()
        if n_imagenes == 0:
            print("❌ No se encontraron imágenes limpias recientes.")
            return None

        # Calcular la mediana para limpiar remanentes
        imagen_final = coleccion_limpia.median().clip(roi)

        parametros = {
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 2500,
            'scale': 20, 
            'region': roi,
            'format': 'png'
        }

        url = imagen_final.getThumbURL(parametros)
        resp = requests.get(url, timeout=60)

        ruta_salida = "avila_color_real.png"
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            img.save(ruta_salida)
            print(f"✅ Imagen color real guardada exitosamente: {ruta_salida}")
            return ruta_salida
        else:
            return None

    except Exception as e:
        print(f"⚠️ Error generando el mapa color real: {e}")
        return None
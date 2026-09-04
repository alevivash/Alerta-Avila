# Hotspots Detector - Script 20 - Detecta focos de calor en El Ávila usando FIRMS y los vectoriza
# Este script se encarga de extraer los focos de calor del catálogo FIRMS,  

import ee
import datetime

# Inicializar
# ee.Initialize(project='alertas-temprana-avila') # CORREGIDO: Ahora se inicializa en main.py

def obtener_vectores_fuego(roi):
    """
    Extrae focos de calor del catálogo FIRMS y los vectoriza a centroides (Puntos).
    """
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    fecha_str = ayer.strftime('%Y-%m-%d')
    hoy_str = datetime.date.today().strftime('%Y-%m-%d')

    # SE PUEDEN USAR ESTAS FECHAS COMO PRUEBA PARA OBTENER FOCOS HISTÓRICOS
    # fecha_str = '2024-03-20' 
    # hoy_str = '2024-04-10'

    # Obtener la colección raster diaria
    firms = (ee.ImageCollection('FIRMS')
             .filterBounds(roi)
             .filterDate(fecha_str, hoy_str))
             
    # --- EL MINI-SALVAVIDAS ---
    # Si hoy no hay incendios, devolvemos "None" silenciosamente
    # Así evitamos el error matemático y dejamos que main.py envíe el reporte preventivo
    if firms.size().getInfo() == 0:
        return None

    # Aplastar en una sola imagen con la temperatura máxima del día
    fuego_max = firms.select('T21').max().toInt16() 

    # Creamos una máscara para asegurarnos de que solo procesamos píxeles calientes
    fuego_mascara = fuego_max.gt(0) 
    imagen_fuego_limpia = fuego_max.updateMask(fuego_mascara)

    # Convertimos los píxeles en Puntos (FeatureCollection)
    focos_vectoriales = imagen_fuego_limpia.reduceToVectors(
        geometry=roi,
        crs=imagen_fuego_limpia.projection(),
        scale=1000, 
        geometryType='centroid', 
        eightConnected=True,
        maxPixels=1e8
    )
    
    # Retornamos los vectores para que main.py los use
    return focos_vectoriales

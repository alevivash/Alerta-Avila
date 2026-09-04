# Hotspots Detector - Script 20 - Detecta focos de calor en El Ávila usando FIRMS y los vectoriza
# Este script se encarga de extraer los focos de calor del catálogo FIRMS,  

import ee
import datetime
import json

# Inicializar
#ee.Initialize(project='alertas-temprana-avila') # CORREGIDO: Ahora se inicializa en main.py para evitar conflictos de inicialización múltiple al importar el módulo

def obtener_vectores_fuego(roi):
    """
    Extrae focos de calor del catálogo FIRMS y los vectoriza a centroides (Puntos).
    """
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    fecha_str = ayer.strftime('%Y-%m-%d')
    hoy_str = datetime.date.today().strftime('%Y-%m-%d')


    # SE PUEDEN USAR ESTAS FECHAS COMO PRUEBA PARA OBTENER FOCOS HISTÓRICOS
    #fecha_str = '2024-03-20' 
    #hoy_str = '2024-04-10'
    
    # Obtener la colección raster diaria
    firms = (ee.ImageCollection('FIRMS')
             .filterBounds(roi)
             .filterDate(fecha_str, hoy_str))

    # STOP: Verificar si la colección está vacía: Sin esto el script muere, tras intenrar colocar los puntos de fuego en el mapa cuando no hay.
    if firms.size().getInfo() == 0:
        return None
    
    # Aplastar en una sola imagen con la temperatura máxima del día
    fuego_max = firms.select('T21').max().toInt16() # T21 es la banda de temperatura de FIRMS, convertida a entero para facilitar la máscara
    
    # Creamos una máscara para asegurarnos de que solo procesamos píxeles calientes
    # (FIRMS asigna valores altos a T21, o puedes usar la banda 'confidence')
    fuego_mascara = fuego_max.gt(0) 
    imagen_fuego_limpia = fuego_max.updateMask(fuego_mascara)
    
    # Convertimos los píxeles en Puntos (FeatureCollection)
    focos_vectoriales = imagen_fuego_limpia.reduceToVectors(
        geometry=roi,
        crs=imagen_fuego_limpia.projection(),
        scale=1000, # Resolución espacial de FIRMS/MODIS
        geometryType='centroid', # Esto convierte el cuadro del píxel en un punto central
        eightConnected=True,
        maxPixels=1e8
    )
    
    return focos_vectoriales

# Cargar región de interés desde un archivo GeoJSON local
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

focos_detectados = obtener_vectores_fuego(roi)

# STOP: Si la función nos devolvió "None", detiene todo antes de contar
if focos_detectados is None:
    print("✅ Bosque seguro. No hay anomalías térmicas en FIRMS hoy.")
    import os
    import sys
    if os.path.exists('focos_activos.geojson'):
        os.remove('focos_activos.geojson')
    sys.exit(0)

# Validar si hay incendios
cantidad = focos_detectados.size().getInfo()

if cantidad > 0:
    print(f" ¡ALERTA TÁCTICA! Se detectaron {cantidad} puntos de fuego.")
    
    # EXTRAER DATOS EN FORMATO GEOJSON PARA EL CRUCE CON EL SCRIPT 1
    geojson_focos = focos_detectados.getInfo()
    
    # Guardamos los puntos en un archivo local para que el Script 1 pueda leerlo y pintarlo encima
    with open('focos_activos.geojson', 'w', encoding='utf-8') as f:
        json.dump(geojson_focos, f, ensure_ascii=False, indent=4)
    print("Archivo 'focos_activos.geojson' generado para el cruce analítico.")
    
    # EXTRAER COORDENADAS PARA TELEGRAM
    lista_focos = geojson_focos['features']
    for i, foco in enumerate(lista_focos):
        lon, lat = foco['geometry']['coordinates']
        link_maps = f"https://www.google.com/maps?q={lat},{lon}" # Corregido enlace estándar de Maps
        print(f"Foco {i+1}: {link_maps}")
        
else:
    print("✅ Bosque seguro. No hay anomalías térmicas recientes.")
    # Si no hay fuego, nos aseguramos de borrar el archivo viejo para no arrastrar alertas pasadas
    import os
    if os.path.exists('focos_activos.geojson'):
        os.remove('focos_activos.geojson')
    import sys
    sys.exit(0)

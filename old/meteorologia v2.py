#version 2.0 - Mejoras en la estructura del código, manejo de errores y formato de salida.
#version 3.0 - Se agregó una función para guardar el historial de datos meteorológicos en un archivo CSV, permitiendo un seguimiento a largo plazo de las condiciones climáticas en el Waraira Repano.
# Este script se encarga de consultar la API de Open-Meteo para obtener las condiciones meteorológicas actuales en puntos estratégicos del Waraira Repano (El Ávila).
# Se han agregado más puntos de interés, mejorado el formato de salida y se ha implement

import requests
import datetime
import time
import os
import csv

# Sesión persistente para evitar bloqueos de red
session = requests.Session()

# Diccionario de puntos estratégicos en El Ávila
ubicaciones_estrategicas = {
    "Picacho_Galipan": {"lat": 10.5608, "lon": -66.9022},
    "Galipan_Central": {"lat": 10.5592, "lon": -66.8911},
    "Hotel_Humboldt": {"lat": 10.5514, "lon": -66.8856},
    "Hoyo_de_la_Cumbre": {"lat": 10.5539, "lon": -66.8625},
    "Pico_Occidental": {"lat": 10.5436, "lon": -66.8333},
    "Asiento_de_Silla": {"lat": 10.5367, "lon": -66.8144},
    "Pico_Oriental": {"lat": 10.5394, "lon": -66.8111},
    "La_Julia": {"lat": 10.5056, "lon": -66.8203},
    "Topo_Goering": {"lat": 10.5228, "lon": -66.8042},
    "Pico_Naiguata": {"lat": 10.5428, "lon": -66.7828},
    "Fila_Maestra": {"lat": 10.5381, "lon": -66.7553},
    "Cascada_Norte": {"lat": 10.5528, "lon": -66.6953},
    "Izcaragua": {"lat": 10.4992, "lon": -66.7264}
}

def guardar_historial_csv(nombre_estacion, clima):
    """Guarda los datos consultados en una base de datos plana CSV."""
    archivo = 'historial_climatico.csv'
    existe = os.path.exists(archivo)
    
    with open(archivo, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha_Hora', 'Estacion', 'Temp_C', 'Humedad_%', 'Viento_kmh', 'Radiacion_Wm2'])
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_estacion, clima['temperature_2m'], clima['relative_humidity_2m'], clima['wind_speed_10m'], clima['direct_radiation']])

def obtener_clima_actual(lat, lon):
    """Consulta la API de Open-Meteo con sistema de reintentos."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "direct_radiation"],
        "timezone": "America/Caracas"
    }
    
    for intento in range(3):
        try:
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()['current']
        except Exception as e:
            print(f"⚠️ Intento {intento+1} fallido para ({lat}, {lon}): {e}")
            time.sleep(2)
    return None

def obtener_reporte_completo(puntos):
    """Recorre las ubicaciones, extrae el clima y lo guarda en el CSV."""
    reporte = {}
    for nombre, coords in puntos.items():
        print(f"📡 Consultando y guardando: {nombre}...")
        datos = obtener_clima_actual(coords['lat'], coords['lon'])
        
        if datos:
            reporte[nombre] = datos
            guardar_historial_csv(nombre, datos) # <--- AQUÍ OCURRE LA MAGIA DEL GUARDADO
            
        time.sleep(0.5) # Pausa estratégica
    return reporte

# Ejecución de prueba
if __name__ == "__main__":
    print("📡 Iniciando recolección de datos meteorológicos...")
    resultado = obtener_reporte_completo(ubicaciones_estrategicas)
    print("\n✅ Proceso completado. Revisa el archivo 'historial_climatico.csv'.")
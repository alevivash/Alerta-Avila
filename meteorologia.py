#version 2.0 - Mejoras en la estructura del código, manejo de errores y formato de salida.
# Este script se encarga de consultar la API de Open-Meteo para obtener las condiciones meteorológicas actuales en puntos estratégicos del Waraira Repano (El Ávila).
# Se han agregado más puntos de interés, mejorado el formato de salida y se ha implement

import requests
import datetime

# Diccionario de puntos estratégicos en El Ávila
ubicaciones_estrategicas = {
    "Galipan_Central": {"lat": 10.5592, "lon": -66.8911},
    "Hotel_Humboldt": {"lat": 10.5514, "lon": -66.8856},
    "Hoyo_de_la_Cumbre": {"lat": 10.5539, "lon": -66.8625},
    "Pico_Occidental": {"lat": 10.5436, "lon": -66.8333},
    "Pico_Oriental": {"lat": 10.5394, "lon": -66.8111},
    "La_Julia": {"lat": 10.5056, "lon": -66.8203},
    "Pico_Naiguata": {"lat": 10.5428, "lon": -66.7828},
    "Fila_Maestra": {"lat": 10.5381, "lon": -66.7553},
}

def obtener_clima_actual(lat, lon):
    """
    Consulta la API de Open-Meteo para obtener condiciones meteorológicas.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "direct_radiation"],
        "timezone": "America/Caracas"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['current']
    except Exception as e:
        print(f"❌ Error consultando punto ({lat}, {lon}): {e}")
        return None

def obtener_reporte_completo(puntos):
    """
    Recorre el diccionario de puntos y retorna un reporte con el clima de cada uno.
    """
    reporte = {}
    for nombre, coords in puntos.items():
        datos = obtener_clima_actual(coords['lat'], coords['lon'])
        if datos:
            reporte[nombre] = datos
    return reporte

# Esta parte permite ejecutar el script individualmente para pruebas
if __name__ == "__main__":
    print("📡 Escaneando puntos meteorológicos en El Ávila...")
    resultado = obtener_reporte_completo(ubicaciones_estrategicas)
    
    for nombre, clima in resultado.items():
        print(f"\n📍 {nombre}:")
        print(f"   🌡️ {clima['temperature_2m']}°C | 💧 {clima['relative_humidity_2m']}% Humedad")
        print(f"   💨 {clima['wind_speed_10m']} km/h | ☀️ {clima['direct_radiation']} W/m²")
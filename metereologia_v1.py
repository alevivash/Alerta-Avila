import requests
import datetime

def obtener_clima_actual(lat, lon):
    """
    Consulta la API de Open-Meteo para obtener condiciones meteorológicas.
    Variables seleccionadas: Temperatura, Humedad, Viento y Radiación Solar.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m", 
            "relative_humidity_2m", 
            "wind_speed_10m", 
            "direct_radiation"
        ],
        "timezone": "America/Caracas"
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() # Lanza error si la API falla
        datos = response.json()['current']
        
        return {
            "temp_c": datos['temperature_2m'],
            "humedad_relativa": datos['relative_humidity_2m'],
            "viento_kmh": datos['wind_speed_10m'],
            "radiacion_wm2": datos['direct_radiation'],
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"❌ Error al consultar Open-Meteo: {e}")
        return None

# --- EJEMPLO DE PRUEBA ---
if __name__ == "__main__":
    # Coordenadas de prueba (Sabas Nieves, El Ávila)
    lat_test, lon_test = 10.5120, -66.8650
    
    clima = obtener_clima_actual(lat_test, lon_test)
    
    if clima:
        print("🌤️ Datos meteorológicos obtenidos exitosamente:")
        print(f"Temperatura: {clima['temp_c']} °C")
        print(f"Humedad: {clima['humedad_relativa']} %")
        print(f"Viento: {clima['viento_kmh']} km/h")
        print(f"Radiación: {clima['radiacion_wm2']} W/m²")
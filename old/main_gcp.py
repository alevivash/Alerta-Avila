import os
import json
import google.auth
import ee
import hotspots_detector
import meteorologia
import analisis_vegetacion_nbr
import functions_framework

def inicializar_earth_engine():
    """Inicializa GEE usando las credenciales automáticas de la Cloud Function."""
    try:
        # GCP detecta automáticamente la cuenta de servicio que ejecuta la función
        credenciales, proyecto_id = google.auth.default(
            scopes=['https://www.googleapis.com/auth/earthengine', 'https://www.googleapis.com/auth/cloud-platform']
        )
        ee.Initialize(credentials=credenciales, project='alertas-temprana-avila')
        print("✅ Earth Engine inicializado correctamente en GCP.")
    except Exception as e:
        print(f"❌ Error al inicializar Earth Engine: {e}")
        raise e

# Registramos la función para que responda a peticiones HTTP
@functions_framework.http
def monitorear_avila_gcp(request):
    print("🚀 Cloud Function activada: Iniciando escaneo del Waraira Repano...")
    
    # Inicializamos GEE dentro del entorno del servidor
    inicializar_earth_engine()
    
    # Cargar el área de interés desde el directorio local de la función
    geojson_path = os.path.join(os.path.dirname(__file__), 'el_avila_waraira_repano.geojson')
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    roi = ee.Geometry(geojson_data['features'][0]['geometry'])
    
    # 1. Detectar focos
    focos_detectados = hotspots_detector.obtener_vectores_fuego(roi)
    cantidad = focos_detectados.size().getInfo()
    
    if cantidad > 0:
        print(f"🔥 ALERTA: {cantidad} focos detectados.")
        analisis_vegetacion_nbr.generar_mapa_con_focos()
        
        lista_focos = focos_detectados.getInfo()['features']
        for foco in lista_focos:
            lon, lat = foco['geometry']['coordinates']
            clima = meteorologia.obtener_clima_actual(lat, lon)
            
            if clima:
                mensaje = (
                    f"📍 Ubicación del Incendio: {lat}, {lon}\n"
                    f"   🌡️ Temp: {clima['temperature_2m']}°C | "
                    f"💧 Humedad: {clima['relative_humidity_2m']}%\n"
                    f"   💨 Viento: {clima['wind_speed_10m']} km/h"
                )
                print(mensaje)
                # Aquí se llamará a la API de Telegram para enviar la alerta real
    else:
        print("✅ No hay focos de calor activos. Iniciando monitoreo preventivo...")
        puntos_control = {
            "Sector La Julia": {"lat": 10.5056, "lon": -66.8203},
            "Estacion Humboldt": {"lat": 10.5514, "lon": -66.8856},
            "Pico Naiguata": {"lat": 10.5428, "lon": -66.7828}
        }
        
        reporte_clima = meteorologia.obtener_reporte_completo(puntos_control)
        # Nota: En Cloud Functions el almacenamiento es efímero (/tmp). 
        # Si deseas guardar el CSV a largo plazo, deberás escribirlo en un bucket de Cloud Storage.
        for nombre, clima in reporte_clima.items():
            print(f"📍 {nombre}: {clima['temperature_2m']}°C, {clima['relative_humidity_2m']}% HR")

    # Retornamos una respuesta HTTP exitosa obligatoria para la función
    return "Procesamiento completado con éxito", 200
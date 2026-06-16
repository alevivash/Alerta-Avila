import os
import json
import ee
import hotspots_detector
import meteorologia
import analisis_vegetacion_nbr

# Inicializar Earth Engine
ee.Initialize(project='alertas-temprana-avila')

# Cargar el área de interés
geojson_path = 'el_avila_waraira_repano.geojson'
with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)
roi = ee.Geometry(geojson_data['features'][0]['geometry'])

def ejecutar_sistema():
    print("🚀 Iniciando escaneo del Waraira Repano...")
    
    # 1. Detectar focos (Script: hotspots_detector.py)
    focos_detectados = hotspots_detector.obtener_vectores_fuego(roi)
    cantidad = focos_detectados.size().getInfo()
    
    if cantidad > 0:
        print(f"🔥 ALERTA: {cantidad} focos detectados.")
        
        # 2. Generar mapa visual cruzado (Script: analisis_vegetacion_nbr.py)
        analisis_vegetacion_nbr.generar_mapa_con_focos()
        
        # 3. Consultar clima en los puntos donde hay focos
        lista_focos = focos_detectados.getInfo()['features']
        
        print("\n📊 Contexto meteorológico en zonas de incendio:")
        for foco in lista_focos:
            lon, lat = foco['geometry']['coordinates']
            clima = meteorologia.obtener_clima_actual(lat, lon)
            
            if clima:
                mensaje = (
                    f"📍 Ubicación del Incendio: {lat}, {lon}\n"
                    f"   实时 Temp: {clima['temperature_2m']}°C | "
                    f"💧 Humedad: {clima['relative_humidity_2m']}%\n"
                    f"   💨 Viento: {clima['wind_speed_10m']} km/h"
                )
                print(mensaje)
            
    else:
        print("✅ No hay focos de calor activos. Sistema en modo de observación preventiva.")
        
        # =====================================================================
        # MONITOREO PREVENTIVO: ANÁLISIS DE GRADIENTE TÉRMICO VERTICAL
        # =====================================================================
        print("\n🌤️ Reporte Climático de Control (Perfil Altitudinal del Parque):")
        
        # Tres estaciones de control representativas en faldas, zona media y cumbre
        puntos_control = {
            "Sector La Julia (Falda / Interfaz Urbana - Cota Baja)": {"lat": 10.5056, "lon": -66.8203},
            "Estación Humboldt (Eje Central / Nubosidad - Cota Media)": {"lat": 10.5514, "lon": -66.8856},
            "Pico Naiguatá (Cumbre Máxima / Alta Montaña - Cota Alta)": {"lat": 10.5428, "lon": -66.7828}
        }
        
        for nombre, coords in puntos_control.items():
            clima = meteorologia.obtener_clima_actual(coords['lat'], coords['lon'])
            
            if clima:
                print(f"📍 {nombre}:")
                print(f"   🌡️ Temperatura: {clima['temperature_2m']} °C")
                print(f"   💧 Humedad Relativa: {clima['relative_humidity_2m']} %")
                print(f"   💨 Vel. Viento: {clima['wind_speed_10m']} km/h")
                print(f"   ☀️ Radiación Directa: {clima['direct_radiation']} W/m²\n")
        
        # Limpieza de archivos temporales
        if os.path.exists('focos_activos.geojson'):
            os.remove('focos_activos.geojson')

if __name__ == "__main__":
    ejecutar_sistema()
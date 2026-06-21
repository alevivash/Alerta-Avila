#version 1.0 - 2026-05-15 - Alejandro Vivas

import os
import json
import ee
import hotspots_detector
import meteorologia
import analisis_vegetacion_nbr
import notificaciones 
import analisis_color_real

# Inicializar Earth Engine
ee.Initialize(project='alertas-temprana-avila')

# Cargar el área de interés
geojson_path = 'el_avila_waraira_repano.geojson'
with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)
roi = ee.Geometry(geojson_data['features'][0]['geometry'])

def ejecutar_sistema():
    print("🚀 Iniciando escaneo del Waraira Repano...")
    
    focos_detectados = hotspots_detector.obtener_vectores_fuego(roi)
    cantidad = focos_detectados.size().getInfo()
    
    if cantidad > 0:
        # 1. Empezamos a redactar el reporte y lo imprimimos
        reporte = f"🔥 ALERTA WARAIRA REPANO: {cantidad} focos detectados.\n\n"
        print(f"🔥 ALERTA: {cantidad} focos detectados.")
        
        # Generar mapa visual cruzado
        analisis_vegetacion_nbr.generar_mapa_con_focos()
        
        lista_focos = focos_detectados.getInfo()['features']
        
        for foco in lista_focos:
            lon, lat = foco['geometry']['coordinates']
            clima = meteorologia.obtener_clima_actual(lat, lon)
            
            if clima:
                # 2. Redactamos la información climática
                datos_clima = (
                    f"📍 Ubicación: {lat}, {lon}\n"
                    f"   🌡️ Temp: {clima['temperature_2m']}°C | "
                    f"💧 Humedad: {clima['relative_humidity_2m']}%\n"
                    f"   💨 Viento: {clima['wind_speed_10m']} km/h\n\n"
                )
                reporte += datos_clima # Lo sumamos al reporte final
                print(datos_clima)     # Lo mostramos en el terminal
                
        # 3. Enviamos a Telegram todo el texto agrupado + la imagen
        # (Asegúrate de que 'alerta_avila_nbr.png' sea el nombre correcto de tu imagen)
        notificaciones.enviar_telegram(reporte, "alerta_avila_nbr.png")
            
    else:
        # Hacemos lo mismo para el modo preventivo
        reporte = "✅ No hay focos de calor activos. Sistema en modo preventivo:\n\n"
        print("✅ No hay focos de calor activos. Sistema en modo de observación preventiva.")
        
        puntos_control = {
            "Sector La Julia (Falda)": {"lat": 10.5056, "lon": -66.8203},
            "Estación Humboldt (Cota Media)": {"lat": 10.5514, "lon": -66.8856},
            "Pico Naiguatá (Cota Alta)": {"lat": 10.5428, "lon": -66.7828}
        }
        
        reporte_clima = meteorologia.obtener_reporte_completo(puntos_control)
        
        for nombre, clima in reporte_clima.items():
            linea_clima = (
                f"📍 {nombre}:\n"
                f"   🌡️ Temp: {clima['temperature_2m']} °C | 💧 Humedad: {clima['relative_humidity_2m']} %\n"
                f"   💨 Viento: {clima['wind_speed_10m']} km/h\n\n"
            )
            reporte += linea_clima # Lo sumamos al reporte final
            print(linea_clima)     # Lo mostramos en el terminal
            
        # Generamos el mapa preventivo a color real y obtenemos su ruta local
        ruta_mapa_preventivo = analisis_color_real.descargar_mapa_preventivo(roi)

        # Enviamos a Telegram el reporte preventivo + el mapa a color real
        notificaciones.enviar_telegram(reporte, ruta_mapa_preventivo)
        
        if os.path.exists('focos_activos.geojson'):
            os.remove('focos_activos.geojson')

if __name__ == "__main__":
    ejecutar_sistema()
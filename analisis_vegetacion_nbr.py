# Áreas Quemadas en El Ávila - Script 19 - Detección de áreas quemadas usando Sentinel-2 y NBR
# Este script se encarga de detectar áreas quemadas en El Ávila utilizando imágenes Sentinel
# version estable 16-05-2026 - Alejandro Vivas

import ee
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import datetime as date

# =====================================================================
# FUNCIONES AUXILIARES: MÁSCARA DE PROBABILIDAD AVANZADA Y JOIN
# =====================================================================
def obtener_coleccion_unida(roi, fecha_inicio, fecha_fin):
    """Acopla la colección Sentinel-2 óptica con su respectiva probabilidad de nubes."""
    s2_sr = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
             .filterBounds(roi)
             .filterDate(fecha_inicio, fecha_fin)
             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)))

    s2_clouds = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                 .filterBounds(roi)
                 .filterDate(fecha_inicio, fecha_fin))

    return ee.ImageCollection(ee.Join.saveFirst('cloud_mask').apply(
        primary=s2_sr,
        secondary=s2_clouds,
        condition=ee.Filter.equals(leftField='system:index', rightField='system:index')
    ))

def mask_s2_clouds(image):
    """Aplica la máscara de probabilidad píxel a píxel para borrar nubes y sombras."""
    cloud_img = ee.Image(image.get('cloud_mask'))
    cld_prb = cloud_img.select('probability')
    
    # Umbral óptimo del 25% para el relieve del Ávila
    is_cloud = cld_prb.gt(25) 
    return image.updateMask(is_cloud.Not())

# =====================================================================
# FUNCIÓN PRINCIPAL PARA EL ORQUESTADOR
# =====================================================================
def generar_mapa_con_focos(roi):
    """
    Evalúa anomalías térmicas recientes frente al histórico, 
    calcula Delta NBR y genera un PNG con estampa de tiempo.
    """
    print("🔥 Iniciando análisis de severidad de quema (Delta NBR)...")
    try:
        # Fechas dinámicas: Buscamos imágenes recientes de los últimos 15 días
        fecha_fin_actual = date.datetime.now()
        fecha_inicio_actual = fecha_fin_actual - date.timedelta(days=15)
        
        f_fin_str = fecha_fin_actual.strftime('%Y-%m-%d')
        f_ini_str = fecha_inicio_actual.strftime('%Y-%m-%d')

        coleccion_base = obtener_coleccion_unida(roi, f_ini_str, f_fin_str)
        sentinel_coleccion_limpia = coleccion_base.map(mask_s2_clouds)

        conteo = sentinel_coleccion_limpia.size().getInfo()
        print(f"Imágenes base limpias recientes encontradas: {conteo}")

        if conteo == 0:
            print("❌ No se encontraron imágenes recientes para calcular NBR actual.")
            return None

        imagen_referencia = sentinel_coleccion_limpia.sort('system:time_start', False).first()
        fecha_actual = ee.Date(imagen_referencia.get('system:time_start'))
        
        imagen_actual_limpia = sentinel_coleccion_limpia.median()
        
        # CAMBIO A NBR: Usamos B8A (NIR) y B12 (SWIR)
        nbr_actual = imagen_actual_limpia.normalizedDifference(['B8A', 'B12']).rename('NBR_actual')
        
        # Histórico: 45 días antes de la imagen actual encontrada
        fecha_inicio_historico = fecha_actual.advance(-45, 'day')
        
        coleccion_hist_base = obtener_coleccion_unida(roi, fecha_inicio_historico, fecha_actual)
        coleccion_historica_limpia = coleccion_hist_base.map(mask_s2_clouds)
        
        conteo_hist = coleccion_historica_limpia.size().getInfo()
        print(f"Imágenes históricas encontradas para promediar: {conteo_hist}")
        
        if conteo_hist == 0:
            print("❌ La colección histórica está vacía. No se puede calcular Delta NBR.")
            return None

        # NBR HISTÓRICO
        nbr_historico_promedio = (coleccion_historica_limpia
                                  .map(lambda img: img.normalizedDifference(['B8A', 'B12']))
                                  .median()
                                  .rename('NBR_hist'))

        # DELTA NBR (Diferencial temporal porcentual)
        delta_nbr = (nbr_actual.subtract(nbr_historico_promedio)
                      .divide(nbr_historico_promedio)
                      .multiply(100)
                      .rename('Delta_NBR'))
        
        delta_avila = delta_nbr.clip(roi)
        print("¡Éxito en la Fase Analítica con NBR!")
        
        # =====================================================================
        # DESCARGA DEL MAPA VISUAL Y APLICACIÓN DE ESTAMPA
        # =====================================================================
        parametros_visuales = {
            'min': -40, 
            'max': 0,
            'palette': ['red', 'yellow', 'green'],
            'dimensions': 1200, 
            'region': roi,
            'format': 'png'
        }
        
        print("Descargando mapa de alertas matemáticas (Delta NBR)...")
        url_mapa = delta_avila.getThumbURL(parametros_visuales)
        respuesta = requests.get(url_mapa, timeout=60)
        
        if respuesta.status_code == 200:
            # 1. Abrimos la imagen NBR recibida
            img = Image.open(BytesIO(respuesta.content)).convert("RGBA")
            
            # 2. Creamos la capa para el texto
            txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
            d = ImageDraw.Draw(txt_layer)
            
            # 3. Ponemos la fecha y hora exacta del momento en que se detectó la anomalía hoy
            fecha_hoy = date.datetime.now().strftime("%Y-%m-%d %H:%M")
            texto_estampa = f"Análisis Delta NBR | Alerta Fuego Activa: {fecha_hoy}"
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except IOError:
                font = ImageFont.load_default()
                
            posicion = (20, img.size[1] - 50)
            
            # 4. Dibujamos el recuadro negro de fondo
            text_bbox = d.textbbox(posicion, texto_estampa, font=font)
            fondo_bbox = [text_bbox[0] - 10, text_bbox[1] - 5, text_bbox[2] + 10, text_bbox[3] + 5]
            d.rectangle(fondo_bbox, fill=(0, 0, 0, 160))
            
            # 5. Dibujamos el texto blanco
            d.text(posicion, texto_estampa, fill=(255, 255, 255, 255), font=font)
            
            # 6. Acoplamos y guardamos
            final_img = Image.alpha_composite(img, txt_layer).convert("RGB")
            ruta_salida = "alerta_avila_nbr.png"
            final_img.save(ruta_salida) 
            
            print(f"👉 ¡Éxito! Archivo '{ruta_salida}' actualizado y marcado.")
            return ruta_salida
        else:
            print(f"❌ Error HTTP al descargar la imagen: {respuesta.status_code}")
            return None

    except Exception as e:
        print(f"⚠️ Error en la generación del mapa NBR: {e}")
        return None

    

# Bibliografía:
# - Documentación oficial de GEE: https://developers.google.com/earth-engine/guides/python_install
# - Tutorial de Sentinel-2 con S2Cloudless:
#  https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless
# NBR: El cambio a NBR es estratégico para detectar áreas quemadas, ya que esta banda es más sensible a la vegetación afectada por incendios. Sin embargo, el NDVI sigue siendo útil para monitorear la salud general de la vegetación. En futuras iteraciones, podríamos generar ambos índices para un análisis más completo.
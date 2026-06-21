import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # Busca un archivo llamado .env y carga sus variables
except ImportError:
    pass

def enviar_telegram(mensaje, ruta_imagen=None):
    # El código ahora busca estas llaves en la memoria del sistema
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Validación de seguridad por si olvidaste configurarlas
    if not TOKEN or not CHAT_ID:
        print("⚠️ Error: Las variables de entorno TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están definidas.")
        return False

    url_mensaje = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    
    try:
        if ruta_imagen and os.path.exists(ruta_imagen):
            with open(ruta_imagen, 'rb') as foto:
                payload = {'chat_id': CHAT_ID, 'caption': mensaje}
                files = {'photo': foto}
                resp = requests.post(url_foto, data=payload, files=files, timeout=30)
        else:
            payload = {'chat_id': CHAT_ID, 'text': mensaje}
            resp = requests.post(url_mensaje, data=payload, timeout=30)
            
        if resp.status_code == 200:
            print("✅ Notificación enviada a Telegram con éxito.")
            return True
        else:
            print(f"❌ Error al enviar a Telegram: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error en el módulo de notificaciones: {e}")
        return False
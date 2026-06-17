import requests
import os

def enviar_telegram(mensaje, ruta_imagen=None):
    # Usa variables de entorno o constantes aquí
    TOKEN = "8805229300:AAG4v5u_i3QdzZsXD7P4gLNM4XRF6ltt03Y"
    CHAT_ID = "1533203515"
    
    url_mensaje = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        # Enviar mensaje de texto
        requests.post(url_mensaje, data={"chat_id": CHAT_ID, "text": mensaje})
        
        # Enviar imagen si existe
        if ruta_imagen and os.path.exists(ruta_imagen):
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            with open(ruta_imagen, 'rb') as foto:
                requests.post(url_foto, data={"chat_id": CHAT_ID}, files={"photo": foto})
        return True
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False
import requests

TOKEN = "xxxx" # El de BotFather
CHAT_ID = "1533203515"           # El de userinfobot

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mensaje = "🏔️ ¡Prueba exitosa! El sistema de monitoreo del Waraira Repano está conectado."

print("Enviando mensaje...")
respuesta = requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})

if respuesta.status_code == 200:
    print("✅ ¡Mensaje enviado! Revisa tu celular.")
else:
    print(f"❌ Error: {respuesta.text}")
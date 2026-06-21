🛰️ Sistema de Alerta Temprana - Waraira Repano / Wildfire Early Warning System
🇪🇸 Español
Monitoreo ambiental automatizado y serverless del Parque Nacional El Ávila, Venezuela. El sistema procesa imágenes satelitales y telemetría climática en tiempo real para enviar alertas tempranas a Telegram y almacenar un registro histórico perpetuo en la nube.

🇺🇸 English
An automated, serverless environmental monitoring system for El Ávila National Park, Venezuela. It processes satellite imagery and real-time weather telemetry to dispatch early warnings via Telegram and log historical data to the cloud.

🛠️ Tecnologías / Tech Stack
Lenguaje: Python 3.11+

Procesamiento Geoespacial: Google Earth Engine (GEE) API

Datos Meteorológicos: Open-Meteo API

Base de Datos en la Nube: Google Sheets API (gspread)

Notificaciones: Telegram Bot API

Despliegue / CI-CD: GitHub Actions

📌 Características / Key Features
🔥 Detección de Focos de Calor / Hotspot Detection: Identificación de anomalías térmicas recientes dentro del polígono del parque.

🗺️ Índice Delta NBR & Color Real: Generación de mapas de severidad de quema (bandas NIR/SWIR) e imágenes RGB diarias con enmascaramiento avanzado de nubes (S2_CLOUD_PROBABILITY).

🌦️ Telemetría Meteorológica / Weather Telemetry: Monitoreo en puntos estratégicos (Temperatura, Humedad, Viento, Precipitación en mm) para evaluar el riesgo de propagación.

☁️ Arquitectura Serverless: Ejecución programada mediante cron jobs en GitHub Actions, sin requerir hardware local.

⚙️ Arquitectura del Sistema / System Architecture
El flujo de datos se ejecuta de forma autónoma siguiendo esta estructura / The data flow executes autonomously following this structure:

Plaintext
[GitHub Actions (Cron)]
│
▼
[main.py] ──── (Orquestador / Orchestrator)
│
├──► [hotspots_detector.py] ──► (GEE: Thermal Anomalies)
│
├──► [meteorologia.py] ──────► (Open-Meteo ➔ Google Sheets)
│
├──► [analisis_*.py] ────────► (GEE: NBR & True Color PNGs)
│
▼
[notificaciones.py] ──► (Telegram API: Text + Images)
🚀 Instalación Local / Local Setup
Para ejecutar o probar el código en una máquina local / To run or test the code on a local machine:

Clonar el repositorio / Clone the repository:

Bash
git clone https://github.com/tu_usuario/Alerta-Avila.git
cd Alerta-Avila
Instalar dependencias / Install dependencies:

Bash
pip install -r requirements.txt
Variables de Entorno / Environment Variables:
Crea un archivo .env en la raíz del proyecto con las siguientes credenciales (protegido por .gitignore) / Create a .env file in the root directory:

Plaintext
TELEGRAM_TOKEN=tu_token_de_telegram
TELEGRAM_CHAT_ID=tu_chat_id
SHEET_ID=tu_id_de_google_sheets
GEE_SERVICE_ACCOUNT_KEY={"type": "service_account", ...}
☁️ Despliegue en la Nube / Cloud Deployment
Para la ejecución automática, configura los siguientes secretos en tu repositorio / For automatic execution, set the following repository secrets (Settings > Secrets and variables > Actions):

Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GEE_SERVICE_ACCOUNT_KEY

Variables: SHEET_ID

Autor / Author: Alejandro Vivas

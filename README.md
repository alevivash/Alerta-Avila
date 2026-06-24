# 🛰️ Sistema de Alerta Temprana - Waraira Repano / Wildfire Early Warning System

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-success.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Serverless-2088FF.svg)

## 🇪🇸 Español

Monitoreo ambiental automatizado y _serverless_ del Parque Nacional El Ávila, Venezuela. El sistema procesa imágenes satelitales y telemetría climática en tiempo real para enviar alertas tempranas a Telegram y almacenar un registro histórico perpetuo en la nube.

## 🇺🇸 English

An automated, serverless environmental monitoring system for El Ávila National Park, Venezuela. It processes satellite imagery and real-time weather telemetry to dispatch early warnings via Telegram and log historical data to the cloud.

---

## 🛠️ Tecnologías / Tech Stack

- **Lenguaje:** Python 3.11+
- **Procesamiento Geoespacial:** Google Earth Engine (GEE) API
- **Datos Meteorológicos:** Open-Meteo API
- **Base de Datos en la Nube:** Google Sheets API (`gspread`)
- **Notificaciones:** Telegram Bot API
- **Despliegue / CI-CD:** GitHub Actions

---

## 📌 Características / Key Features

- **🔥 Detección de Focos de Calor / Hotspot Detection:** Identificación de anomalías térmicas recientes dentro del polígono del parque.
- **🗺️ Índice Delta NBR & Color Real:** Generación de mapas de severidad de quema (bandas NIR/SWIR) e imágenes RGB diarias con enmascaramiento avanzado de nubes (`S2_CLOUD_PROBABILITY`).
- **🌦️ Telemetría Meteorológica / Weather Telemetry:** Monitoreo en puntos estratégicos (Temperatura, Humedad, Viento, Precipitación en mm) para evaluar el riesgo de propagación.
- **☁️ Arquitectura Serverless:** Ejecución programada mediante _cron jobs_ en GitHub Actions, sin requerir hardware local.

---

## 🛰️ Fuente de Datos: Copernicus Sentinel-2 / Data Source

Este sistema se alimenta de la constelación satelital **Sentinel-2** de la Agencia Espacial Europea (ESA), procesada a través de Google Earth Engine. / _This system is powered by the European Space Agency's (ESA) **Sentinel-2** satellite constellation, processed via Google Earth Engine._

- **Resolución Espacial / Spatial Resolution:** 10m - 20m por píxel.
- **Frecuencia de Revisita / Revisit Time:** Aproximadamente cada 5 días.
- **Análisis de Severidad (NBR):** Utiliza las bandas _Near Infrared_ (B8A) y _Short Wave Infrared_ (B12) para evaluar el daño en la biomasa forestal tras un incendio.
- **Visualización (Color Real):** Composiciones RGB utilizando las bandas B4 (Red), B3 (Green) y B2 (Blue).
- **Filtro de Nubes / Cloud Masking:** Implementación del algoritmo `COPERNICUS/S2_CLOUD_PROBABILITY` para garantizar imágenes nítidas sobre la topografía compleja de la montaña.

---

## ⚙️ Arquitectura del Sistema / System Architecture

El flujo de datos se ejecuta de forma autónoma siguiendo esta estructura / _The data flow executes autonomously following this structure_:

```text
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
```

Autor / Author: Alejandro Vivas

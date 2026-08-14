# Leak Tracker 🎧🔒

Sistema para rastrear filtraciones de canciones inéditas mediante marcas de agua
(watermarks) inaudibles, únicas por destinatario.

## Idea

1. Subes una canción y eliges a quién se la vas a enviar (colaborador, sello, prensa...).
2. El sistema incrusta un código único e inaudible en el audio y te devuelve la copia marcada.
3. Si esa canción se filtra, subes el archivo sospechoso y el sistema extrae el código,
   diciéndote exactamente de quién salió.
4. Si hay coincidencia, se dispara un webhook (Slack/Telegram) avisando en tiempo real.

## Arquitectura

```
frontend (HTML simple)
      │
      ▼
backend (FastAPI)
   ├── /watermark   → incrusta el código y guarda el registro
   ├── /verify       → extrae el código de un archivo sospechoso
   └── /webhook-test → dispara una alerta de prueba
      │
      ▼
BBDD (SQLite en dev / PostgreSQL en producción)
```

## Estado de este repo

Esto es el **esqueleto** del proyecto, no el trabajo terminado. Contiene:

- [x] Estructura de carpetas
- [x] Modelo de datos (4 tablas)
- [x] Prototipo funcional de watermark inaudible (embed/extract con FSK en alta frecuencia)
- [x] API mínima con FastAPI
- [ ] Webhook real hacia Slack/Telegram (hay un stub a completar)
- [ ] Frontend
- [ ] Despliegue en Hetzner con Docker

La idea es completar cada pieza pendiente como commits separados (a poder ser,
pidiéndoselo a Claude conectado a este repo), para que el historial de commits
cuente la historia de cómo se construyó.

## Cómo arrancarlo en local

```bash
cd backend
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs para probar los endpoints desde Swagger.

## Probar el watermark por consola (sin la API)

```bash
cd backend
python -m app.watermark embed ejemplo.wav 42 ejemplo_marcado.wav
python -m app.watermark extract ejemplo_marcado.wav
```

## Siguientes pasos sugeridos

1. Completa `backend/app/routes/webhook.py` para que avise de verdad (Slack/Telegram).
2. Cambia SQLite por PostgreSQL en `docker-compose.yml` para producción.
3. Añade un frontend mínimo (formulario de subida + tabla de detecciones).
4. Despliega en un VPS de Hetzner con `docker-compose up -d` detrás de Caddy/nginx.
5. Documenta en el README qué medidas de seguridad tomaste (API keys, rate limiting,
   validación de tamaño/tipo de archivo, etc.) — esa parte también cuenta para el trabajo.

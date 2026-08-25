# Leak Tracker — Estado del proyecto

**Autor:** Raúl
**Repositorio:** github.com/Rulooop/leak_traker
**Contexto:** Trabajo de la formación de ciberseguridad con IA. El enunciado pedía un
proyecto con base de datos, API/webhook, aplicación y repositorio de GitHub con
historial de commits real, construido con ayuda de Claude.

---

## 1. Idea del proyecto

**Leak Tracker** es un sistema para rastrear filtraciones de canciones inéditas
mediante marcas de agua (*watermarks*) de audio inaudibles, únicas por
destinatario.

El flujo es el siguiente:

1. Un artista sube una canción y elige a quién se la va a enviar (colaborador,
   sello, prensa...).
2. El sistema incrusta un código único e inaudible en el audio y devuelve la
   copia marcada, lista para enviar.
3. Si esa canción se filtra en internet, se sube el archivo sospechoso al
   sistema, que extrae el código y dice exactamente de qué copia (y por tanto
   de qué destinatario) salió.
4. Si hay coincidencia, se dispara una alerta automática (webhook) avisando en
   tiempo real.

Encaja con los cuatro bloques que pedía el trabajo: **base de datos**,
**API/webhook**, **aplicación**, y **repositorio de GitHub con historial de
commits**.

---

## 2. Arquitectura

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

**Stack elegido:** Python (FastAPI) para el backend, SQLAlchemy como ORM,
SQLite para desarrollo local y PostgreSQL para producción, Docker/Docker
Compose para el despliegue, y un frontend mínimo en HTML/JS puro para probar
la API sin depender de herramientas externas.

---

## 3. Lo que está hecho

### 3.1 Base de datos (BBDD)

4 tablas relacionadas entre sí:

- **`tracks`** — canciones originales subidas.
- **`recipients`** — destinatarios (colaboradores, sellos, prensa...).
- **`watermarked_files`** — registro de cada copia marcada: qué código se le
  puso, a qué canción y a qué destinatario corresponde.
- **`leak_detections`** — cada vez que se sube un archivo sospechoso, se
  registra el código extraído y si hubo coincidencia.

Definida tanto en el ORM (`backend/app/models.py`) como en SQL puro
(`db/schema.sql`), para poder documentarla como entregable independiente.

### 3.2 Watermark de audio inaudible (el núcleo técnico del proyecto)

Prototipo funcional en `backend/app/watermark.py`, probado de extremo a
extremo:

- Técnica: **FSK (Frequency Shift Keying)** en alta frecuencia (18.5–19.5 kHz,
  casi inaudible para el oído humano).
- El código del destinatario se codifica en binario y se incrusta como una
  secuencia de tonos cortos mezclados a bajo volumen con el audio original.
- La extracción analiza el espectro de frecuencias (FFT) de cada tramo y
  recupera el código.
- **Probado:** se incrustó un código de prueba en un audio sintético, se
  extrajo correctamente, y se validó también el flujo completo subiendo el
  archivo marcado al endpoint `/verify`, que lo identificó sin errores.

### 3.3 API (FastAPI)

- `POST /watermark` — sube una canción + destinatario, devuelve la copia
  marcada y guarda el registro.
- `POST /verify` — sube un archivo sospechoso, extrae el código y dice de
  quién es la filtración si hay coincidencia.
- `POST /recipients` / `GET /recipients` — gestión de destinatarios.
- `POST /webhook-test` — dispara una alerta de prueba manualmente.

### 3.4 Webhook (parcial)

Hay un stub en `backend/app/routes/webhook.py` (`send_alert()`) preparado
para enviar mensajes a Slack/Telegram vía un *Incoming Webhook*. Se dispara
automáticamente cuando `/verify` encuentra una coincidencia. **Falta**
conectarlo a un webhook real (ver sección de pendientes).

### 3.5 Seguridad

Medidas implementadas y documentadas en el propio `README.md`:

- **Autenticación por API key** (cabecera `X-API-Key`) en todos los
  endpoints que crean o consultan datos, usando comparación segura
  (`secrets.compare_digest`) para evitar *timing attacks*.
- **Límite de tamaño de archivo** (50MB) — se corta la subida antes de
  escribir nada a disco, evitando ataques de saturación.
- **Rate limiting** (10 peticiones/minuto por IP) en los endpoints
  sensibles, con `slowapi`.
- **Nombres de archivo generados por el servidor**, nunca por el cliente —
  evita ataques de *path traversal*.
- **Fallo seguro**: si falta la `API_KEY` en la configuración, el servidor
  da error en vez de quedar abierto por descuido.

Todas estas medidas se probaron activamente (no solo se escribieron): se
lanzó el servidor y se comprobó con peticiones reales que cada protección
responde como debe (401 sin clave, 413 con archivo demasiado grande, etc.).

### 3.6 Despliegue (preparado, no probado en real)

`docker-compose.yml` y `Dockerfile` listos para levantar el backend + una
base de datos PostgreSQL con un solo comando, pensado para desplegarse en un
VPS de Hetzner.

### 3.7 Entorno de trabajo y flujo con GitHub

- Máquina virtual con Ubuntu 24.04 LTS montada en VirtualBox, con Git,
  Python, Docker y Claude Code instalados.
- Repositorio creado en GitHub (`Rulooop/leak_traker`) y conectado por SSH
  usando autenticación por token personal.
- Historial de commits real reflejando el proceso de construcción:
  esqueleto inicial → medidas de seguridad → corrección de estructura de
  carpetas.

---

## 4. Lo que falta por hacer

| Tarea | Prioridad | Notas |
|---|---|---|
| Conectar el webhook real (Slack/Telegram) | Alta | Solo falta rellenar `send_alert()` con la URL del webhook y probarlo |
| Desplegar en el VPS de Hetzner | Alta | `docker-compose.yml` ya está listo; falta contratar el VPS, subir el proyecto y poner HTTPS (Caddy o nginx) delante |
| Cargar saldo en Claude Code o seguir completando a mano | Media | Para agilizar el resto de tareas con commits automáticos |
| Pulir el frontend | Media | Ahora mismo es funcional pero muy básico visualmente |
| Cambiar SQLite por PostgreSQL en el flujo real | Media | El `docker-compose.yml` ya lo contempla; falta probarlo de verdad, no solo en local con SQLite |
| Validar el contenido real del archivo (no solo la extensión `.wav`) | Baja | Alguien podría renombrar un archivo distinto como `.wav` |
| Servir los audios solo vía endpoint autenticado | Baja | Ahora mismo se guardan como archivos estáticos accesibles si se conoce la ruta |
| Centralizar el rate limiting si hay varias réplicas del backend | Baja | Solo relevante si se escala a más de una instancia |

---

## 5. Resumen para la entrega

El proyecto cumple con los cuatro requisitos del enunciado (BBDD, API/webhook,
aplicación, GitHub con historial de commits construido con Claude), tiene un
componente técnico propio y no trivial (el watermarking de audio inaudible),
y documenta de forma honesta tanto las decisiones de seguridad tomadas como
lo que queda pendiente — que es tan valioso de mostrar como lo que ya
funciona.

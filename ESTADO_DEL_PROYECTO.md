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
4. Si hay coincidencia, se dispara una alerta automática por Telegram avisando
   en tiempo real.

Encaja con los cuatro bloques que pedía el trabajo: **base de datos**,
**API/webhook**, **aplicación**, y **repositorio de GitHub con historial de
commits**.

---

## 2. Arquitectura

```
frontend (dashboard de una sola página, HTML/CSS/JS sin frameworks)
      │
      ▼
backend (FastAPI)
   ├── /watermark                          → incrusta el código y guarda el registro
   ├── /verify                             → extrae el código de un archivo sospechoso y dispara alerta si hay match
   ├── /recipients                         → crear y listar destinatarios
   ├── /stats /tracks /watermarked-files   → endpoints de solo lectura que alimentan el dashboard
   ├── /leak-detections                    → historial de verificaciones
   ├── /watermarked-files/{id}/download    → descarga autenticada de una copia marcada
   └── /webhook-test                       → dispara una alerta de prueba
      │
      ▼
BBDD (SQLite en dev / PostgreSQL en producción, vía docker-compose)
```

**Stack elegido:** Python (FastAPI) para el backend, SQLAlchemy como ORM,
SQLite para desarrollo local y PostgreSQL para producción, Docker/Docker
Compose para los contenedores, un frontend propio en HTML/CSS/JS puro (sin
frameworks), Telegram Bot API para las alertas, y Cloudflare Tunnel + un
dominio propio (`leaktracker.cloud`) para publicarlo en internet sin pagar un
VPS. Detalle completo en la sección "Stack tecnológico" del `README.md`.

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
  quién es la filtración si hay coincidencia (y dispara la alerta).
- `POST /recipients` / `GET /recipients` — gestión de destinatarios.
- `GET /stats` / `GET /tracks` / `GET /watermarked-files` /
  `GET /leak-detections` — endpoints de solo lectura que alimentan el
  dashboard.
- `GET /watermarked-files/{id}/download` — descarga autenticada de una copia
  marcada (protegida con `X-API-Key`, no es un archivo estático).
- `POST /webhook-test` — dispara una alerta de prueba manualmente.

### 3.4 Alertas por Telegram (conectado y probado)

`send_alert()` en `backend/app/routes/webhook.py` llama directamente a la API
de Telegram (`sendMessage`) usando un bot propio (`@Trackerleakbot`), en vez
del stub genérico de Incoming Webhook que había al principio. El token del
bot y el `chat_id` viven en `.env` (nunca en el código ni en el repo).
Probado end-to-end dos veces: con `/webhook-test` y con un caso real completo
(crear destinatario → generar copia marcada → "filtrarla" → `/verify`) — en
ambos casos la alerta llegó sola a Telegram. La `API_KEY` y el token del bot
se rotaron una vez tras quedar expuestos accidentalmente.

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
- **Descarga solo vía endpoint autenticado**: la carpeta `uploads/` no se
  sirve como estáticos (ni en el backend ni en el nginx del frontend); la
  única forma de descargar una copia marcada es
  `/watermarked-files/{id}/download`, protegido con `X-API-Key`.
- **CORS restringido en producción**: `ALLOWED_ORIGINS` está fijado a
  `https://leaktracker.cloud` (ya no `*`), ahora que la web es pública de
  verdad.

Todas estas medidas se probaron activamente (no solo se escribieron): se
lanzó el servidor y se comprobó con peticiones reales que cada protección
responde como debe (401 sin clave, 413 con archivo demasiado grande, etc.).

Pendiente de securizar (detalle y por qué en el `README.md`): validar el
contenido real del archivo subido (no solo la extensión `.wav`), HTTPS en
local, y centralizar el rate limiting con Redis si algún día hay varias
réplicas del backend.

### 3.6 Despliegue (en producción, probado de verdad)

Se descartó un VPS de pago (Hetzner) a favor de autoalojar el proyecto desde
la propia VM con **Cloudflare Tunnel**, sin coste de servidor:

- Dominio propio `leaktracker.cloud` comprado en IONOS, con el DNS
  gestionado en Cloudflare.
- `docker-compose.yml` levanta los 3 servicios (`db` con PostgreSQL,
  `backend`, `frontend` con nginx) en la VM.
- Un túnel de Cloudflare con nombre fijo (`leak-tracker`) expone
  `leaktracker.cloud` → frontend y `api.leaktracker.cloud` → backend,
  instalado como servicio systemd para que sobreviva a cerrar la terminal o
  reiniciar la VM (no a apagarla).
- Confirmado accesible desde fuera de la VM (probado desde el móvil con
  datos móviles, no wifi).

### 3.7 Entorno de trabajo y flujo con GitHub

- Máquina virtual con Ubuntu 24.04 LTS montada en VirtualBox, con Git,
  Python, Docker y Claude Code instalados.
- Repositorio creado en GitHub (`Rulooop/leak_traker`) y conectado por HTTPS
  con credenciales guardadas localmente.
- Historial de commits real reflejando todo el proceso de construcción, y un
  `DIARIO.md` con el resumen sesión a sesión en lenguaje normal (además del
  historial técnico de commits).

---

## 4. Lo que falta por hacer

| Tarea | Prioridad | Notas |
|---|---|---|
| Validar el contenido real del archivo (no solo la extensión `.wav`) | Media | Alguien podría renombrar un archivo distinto como `.wav`; único pendiente con impacto de seguridad práctico ahora que la web es pública |
| Escáner automático de filtraciones en fuentes externas | Media | Aplazado a propósito (no lo pedía el enunciado); si se retoma, versión mínima con 1-2 fuentes con API oficial (YouTube/SoundCloud) + job programado, en vez de scraping genérico |
| HTTPS en local | Baja | En producción ya lo da Cloudflare Tunnel; en desarrollo local sigue sin HTTPS |
| Centralizar el rate limiting si hay varias réplicas del backend | Baja | Está en memoria por IP; solo relevante si se escala a más de una instancia (con una, como ahora, no es urgente) |

---

## 5. Resumen para la entrega

El proyecto cumple con los cuatro requisitos del enunciado (BBDD, API/webhook,
aplicación, GitHub con historial de commits construido con Claude), tiene un
componente técnico propio y no trivial (el watermarking de audio inaudible),
y ya no se queda en "funciona en local": está desplegado de verdad en
`https://leaktracker.cloud`, con alertas de Telegram reales y probadas. El
proyecto documenta de forma honesta tanto las decisiones de seguridad
tomadas como lo poco que queda pendiente — que es tan valioso de mostrar
como lo que ya funciona.

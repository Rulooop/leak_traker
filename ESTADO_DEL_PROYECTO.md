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
   ├── /support-chat                       → chat de soporte con IA (Claude) sobre cómo funciona LeakTracker
   └── /webhook-test                       → dispara una alerta de prueba
      │
      ▼
BBDD (SQLite en dev / PostgreSQL en producción, vía docker-compose)
```

**Stack elegido:** Python (FastAPI) para el backend, SQLAlchemy como ORM,
SQLite para desarrollo local y PostgreSQL para producción, Docker/Docker
Compose para los contenedores, un frontend propio en HTML/CSS/JS puro (sin
frameworks), Telegram Bot API para las alertas, la API de Claude (Anthropic)
para el chat de soporte del dashboard, y Cloudflare Tunnel + un dominio
propio (`leaktracker.cloud`) para publicarlo en internet sin pagar un VPS.
Detalle completo en la sección "Stack tecnológico" del `README.md`.

---

## 3. Lo que está hecho

### 3.1 Base de datos (BBDD)

5 tablas relacionadas entre sí:

- **`users`** — cuentas de acceso: email, contraseña hasheada, rol
  (admin/usuario) y plan (free/pro).
- **`tracks`** — canciones originales subidas, con su `owner_id` (de qué
  cuenta son).
- **`recipients`** — destinatarios (colaboradores, sellos, prensa...), con
  su `owner_id`.
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

- `POST /auth/register` / `POST /auth/login` — crea cuenta o inicia sesión
  (email + contraseña), devuelve un token de sesión (JWT). `GET /auth/me`
  — datos de la cuenta que ha iniciado sesión.
- `POST /watermark` — sube una canción + destinatario, devuelve la copia
  marcada y guarda el registro a nombre de la cuenta que hizo la petición.
- `POST /verify` — sube un archivo sospechoso, extrae el código y dice de
  quién es la filtración si hay coincidencia entre las canciones de esa
  cuenta (y dispara la alerta).
- `POST /recipients` / `GET /recipients` — gestión de destinatarios, por cuenta.
- `GET /stats` / `GET /tracks` / `GET /watermarked-files` /
  `GET /leak-detections` — endpoints de solo lectura que alimentan el
  dashboard, filtrados por cuenta (salvo para el admin, que ve todo).
- `GET /watermarked-files/{id}/download` — descarga autenticada de una copia
  marcada (requiere sesión y ser el dueño, no es un archivo estático).
- `POST /webhook-test` — dispara una alerta de prueba manualmente.
- `POST /support-chat` — chat de soporte con IA (Claude Haiku 4.5) para
  resolver dudas sobre el funcionamiento del sistema; protegido igual que el
  resto (login + rate limiting), usa `ANTHROPIC_API_KEY` desde `.env`.

### 3.4 Alertas por Telegram (conectado y probado)

`send_alert()` en `backend/app/routes/webhook.py` llama directamente a la API
de Telegram (`sendMessage`) usando un bot propio (`@Trackerleakbot`), en vez
del stub genérico de Incoming Webhook que había al principio. El token del
bot y el `chat_id` viven en `.env` (nunca en el código ni en el repo).
Probado end-to-end dos veces: con `/webhook-test` y con un caso real completo
(crear destinatario → generar copia marcada → "filtrarla" → `/verify`) — en
ambos casos la alerta llegó sola a Telegram. La antigua `API_KEY` y el token
del bot se rotaron una vez tras quedar expuestos accidentalmente (la
`API_KEY` ya no existe, ver 3.5).

### 3.5 Seguridad

Medidas implementadas y documentadas en el propio `README.md`:

- **Login real** en vez de una clave compartida: cuentas con email +
  contraseña hasheada (`bcrypt`) en una tabla `users`, sesión mediante un
  token firmado (JWT, `SECRET_KEY`) que caduca a los 7 días.
- **Datos aislados por cuenta**: cada canción/destinatario tiene un
  `owner_id`; un usuario normal solo ve y usa los suyos (incluida la
  búsqueda de coincidencias en `/verify`). El rol admin ve los de todo el
  mundo, pensado para gestionar planes de pago más adelante (`users.plan`,
  sin Stripe integrado todavía).
- **Límite de tamaño de archivo** (50MB) — se corta la subida antes de
  escribir nada a disco, evitando ataques de saturación.
- **Rate limiting** (10 peticiones/minuto por IP) en los endpoints
  sensibles, incluido `/auth/login` y `/auth/register`, con `slowapi`.
- **Nombres de archivo generados por el servidor**, nunca por el cliente —
  evita ataques de *path traversal*.
- **Fallo seguro**: si falta la `SECRET_KEY` en la configuración, el
  servidor da error en vez de quedar abierto por descuido.
- **Descarga solo vía endpoint autenticado**: la carpeta `uploads/` no se
  sirve como estáticos (ni en el backend ni en el nginx del frontend); la
  única forma de descargar una copia marcada es
  `/watermarked-files/{id}/download`, que exige sesión y ser el dueño.
- **CORS restringido en producción**: `ALLOWED_ORIGINS` está fijado a
  `https://leaktracker.cloud` (ya no `*`), ahora que la web es pública de
  verdad.
- **Validación del contenido real del archivo subido**: `/watermark` y
  `/verify` comprueban la cabecera RIFF/WAVE de los bytes recibidos, no solo
  la extensión `.wav` del nombre; un archivo corrupto o renombrado se
  rechaza con 400 antes de tocar disco.

Todas estas medidas se probaron activamente (no solo se escribieron): se
lanzó el servidor y se comprobó con peticiones reales que cada protección
responde como debe (401 sin sesión, 413 con archivo demasiado grande, etc.).

Pendiente de securizar (detalle y por qué en el `README.md`): HTTPS en
local, centralizar el rate limiting con Redis si algún día hay varias
réplicas del backend, verificación de email y límite de intentos de login
por cuenta.

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

### 3.8 Dashboard interactivo y chat de soporte con IA

Sobre el dashboard ya existente, añadido sin tocar el algoritmo de watermark
ni el esquema de la BBDD:

- **Chat de soporte con IA**: widget flotante (JS puro) conectado a
  `POST /support-chat`, que llama a la API de Claude (Haiku 4.5) con un
  system prompt que conoce el funcionamiento real del sistema. Sin
  persistencia en servidor — el historial vive solo en memoria del navegador.
- **Explicador del watermark**: icono de ayuda junto a las métricas
  relacionadas, con un modal (reutilizable) que explica en lenguaje sencillo
  qué es el watermark y cómo identifica una filtración. El código sigue
  siendo un entero de 16 bits en el backend; el formato `LT-XXXXXX` es solo
  una capa de visualización en el frontend.
- **Más interactividad**: gráfica "Protection Overview" con tooltips de
  fecha/valor exacto, una "Tasa de detección" real (en vez de una métrica de
  "accuracy" inventada, que no se puede calcular sin datos de falsos
  positivos/negativos), sección "Top Tracks", filtros por estado y fecha
  (100% client-side, sin peticiones nuevas al backend), animaciones al pasar
  el ratón por las tarjetas y transiciones suaves entre vistas del menú.

### 3.9 Identidad visual propia

A partir de una imagen de referencia y el logo oficial (aportados por Raúl),
se adoptó la paleta e identidad de marca reales sobre la estructura ya
construida:

- **Paleta**: negro casi puro de fondo, morado como color de marca (botones,
  navegación activa, gráfica), y rojo/naranja/verde para
  filtración/atención/protegido — variables CSS renombradas
  (`--accent`, `--danger`, `--warning`, `--success`) para que el significado
  de cada color quede explícito en el código.
- **Logo real**: icono recortado del logo oficial, con el fondo original
  eliminado (transparencia), en `frontend/assets/logo-icon.png`.
- **Layout**: navbar superior (logo + notificaciones con el nº real de
  filtraciones + acceso a ajustes + estado de conexión) y sidebar con panel
  "Estado del sistema" (derivado del mismo chequeo de conexión que ya
  existía, sin inventar monitorización de servicios que no se pueden
  comprobar). Dashboard reorganizado en grid de 2 columnas, con una sección
  nueva "Actividad reciente" que combina eventos reales ya existentes
  (canciones, copias, detecciones) sin backend nuevo.
- **Límites honestos frente al mockup**: no se copiaron el nombre de usuario
  falso, los "servicios" monitorizados por separado que no existen de
  verdad, ni los porcentajes de confianza por fila que el sistema no calcula.

---

## 4. Lo que falta por hacer

| Tarea | Prioridad | Notas |
|---|---|---|
| Escáner automático de filtraciones en fuentes externas | Media | Aplazado a propósito (no lo pedía el enunciado); si se retoma, versión mínima con 1-2 fuentes con API oficial (YouTube/SoundCloud) + job programado, en vez de scraping genérico |
| HTTPS en local | Baja | En producción ya lo da Cloudflare Tunnel; en desarrollo local sigue sin HTTPS |
| Centralizar el rate limiting si hay varias réplicas del backend | Baja | Está en memoria por IP; solo relevante si se escala a más de una instancia (con una, como ahora, no es urgente) |
| Cobro real (Stripe) para el plan "pro" | Media | La estructura ya está (`users.plan`, rol admin); falta la integración de pago y los límites de uso por plan |

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

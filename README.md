# Leak Tracker 🎧🔒

Sistema para rastrear filtraciones de canciones inéditas mediante marcas de agua
(watermarks) inaudibles, únicas por destinatario.

## Idea

1. Subes una canción y eliges a quién se la vas a enviar (colaborador, sello, prensa...).
2. El sistema incrusta un código único e inaudible en el audio y te devuelve la copia marcada.
3. Si esa canción se filtra, subes el archivo sospechoso y el sistema extrae el código,
   diciéndote exactamente de quién salió.
4. Si hay coincidencia, se dispara una alerta por Telegram avisando en tiempo real.

## Arquitectura

```
frontend (dashboard de una sola página, HTML/CSS/JS sin frameworks)
      │
      ▼
backend (FastAPI)
   ├── /auth/register /auth/login /auth/me → cuenta con email+contraseña, sesión por token (JWT)
   ├── /watermark                          → incrusta el código y guarda el registro
   ├── /verify                             → extrae el código de un archivo sospechoso y dispara alerta si hay match
   ├── /recipients                         → crear y listar destinatarios (de la cuenta que ha iniciado sesión)
   ├── /stats /tracks /watermarked-files   → endpoints de solo lectura que alimentan el dashboard
   ├── /leak-detections                    → historial de verificaciones
   ├── /watermarked-files/{id}/download    → descarga autenticada de una copia marcada
   ├── /support-chat                       → chat de soporte con IA (Claude) sobre cómo funciona LeakTracker
   └── /webhook-test                       → dispara una alerta de prueba
      │
      ▼
BBDD (SQLite en dev / PostgreSQL en producción, vía docker-compose)
```

Multiusuario: cada cuenta (`users.role = "user"`) solo ve sus propias canciones,
destinatarios y filtraciones. La cuenta admin (`role = "admin"`) ve las de
todo el mundo — pensado para más adelante gestionar planes de pago
(`users.plan`, hoy sin cobro real todavía).

## Stack tecnológico

**Backend**
- Python + FastAPI (framework de la API)
- SQLAlchemy (ORM para la base de datos)
- NumPy + SciPy (el watermark de audio, técnica FSK)
- slowapi (rate limiting), httpx (peticiones HTTP salientes)
- SQLite (desarrollo) / PostgreSQL (producción)
- API de Claude (Anthropic) para el chat de soporte con IA del dashboard

**Frontend**
- HTML, CSS y JavaScript puro (sin frameworks)
- Google Fonts: Space Grotesk, Inter, IBM Plex Mono
- SVG generado dinámicamente (la forma de onda y la gráfica "Protection Overview" del dashboard)
- Identidad visual propia: logo real (`frontend/assets/logo-icon.png`) y paleta de marca (negro + morado, con rojo/naranja/verde para los estados de filtración/atención/protegido)

**Infraestructura**
- Docker + Docker Compose (contenedores)
- nginx (sirve el frontend)
- VirtualBox + Ubuntu 24.04 LTS (entorno de desarrollo)

**Despliegue y comunicación**
- Cloudflare (DNS + Cloudflare Tunnel, para exponer la web a internet sin coste de servidor)
- IONOS (registro del dominio leaktracker.cloud)
- Telegram Bot API (alertas de filtración)
- Git + GitHub (control de versiones)

## Estado de este repo

Ya no es solo el esqueleto inicial: el backend, el panel web, las alertas y el
despliegue están funcionando de verdad, en producción. Contiene:

- [x] Estructura de carpetas
- [x] Modelo de datos (5 tablas)
- [x] Prototipo funcional de watermark inaudible (embed/extract con FSK en alta frecuencia)
- [x] API completa con FastAPI (watermark, verify, recipients, dashboard, descarga de archivos)
- [x] Login real: cuentas con email + contraseña hasheada (bcrypt) en BBDD, sesión con JWT, roles admin/usuario y datos aislados por cuenta
- [x] Límite de tamaño de archivo y rate limiting (ver "Seguridad" abajo)
- [x] Frontend propio (login/registro, dashboard, alta de canciones, verificación, destinatarios, cuenta)
- [x] Dashboard interactivo: chat de soporte con IA (Claude), explicador del watermark, gráfica de tendencia con tooltips, filtros por estado/fecha y animaciones
- [x] Identidad visual propia: logo real, paleta de marca, navbar superior y sidebar reestilizado, dashboard en grid de 2 columnas con "Actividad reciente"
- [x] Validación de la cabecera real del archivo subido (RIFF/WAVE) en `/watermark` y `/verify`, no solo la extensión `.wav`
- [x] `docker-compose.yml` probado en local: los 3 servicios (`db`, `backend`, `frontend`) arrancan y responden correctamente
- [x] Alertas por Telegram probadas de verdad (bot propio, `sendMessage` vía API de Telegram) — ver `backend/app/routes/webhook.py`
- [x] Desplegado en internet: autoalojado desde la VM con Cloudflare Tunnel en `https://leaktracker.cloud`, con el túnel como servicio systemd persistente

## Seguridad

Decisiones de seguridad tomadas en este proyecto, y por qué:

**Login real, no una clave compartida.** Todos los endpoints que crean o
consultan datos (`/watermark`, `/verify`, `/recipients`, dashboard...) exigen
haber iniciado sesión: `POST /auth/register` o `/auth/login` devuelven un
token de sesión (JWT, firmado con `SECRET_KEY` — nunca en el código, nunca en
GitHub, está en `.gitignore`) que el frontend manda como cabecera
`Authorization: Bearer <token>`. Las contraseñas nunca se guardan en claro:
se hashean con `bcrypt` antes de tocar la BBDD. El token caduca a los 7 días.

**Datos aislados por cuenta.** Cada `Track`/`Recipient` tiene un `owner_id`.
Un usuario normal (`role = "user"`) solo ve y puede operar sobre sus propias
canciones, destinatarios y filtraciones — tanto en las consultas del
dashboard como en `/watermark` (no puede usar un destinatario de otra
cuenta) y en `/verify` (una filtración solo hace match contra tus propios
watermarks, nunca contra los de otra cuenta). La cuenta admin (`role =
"admin"`) ve los datos de todo el mundo, pensado para la futura gestión de
planes de pago.

**Límite de tamaño de archivo (50MB).** Los endpoints que reciben archivos leen
el cuerpo en trozos de 1MB y cortan la conexión en cuanto se supera el límite,
*antes* de escribir nada a disco. Así evitamos que alguien pueda tumbar el
servicio (o llenar el disco) subiendo un archivo gigante disfrazado de `.wav`.

**Rate limiting (10 peticiones/minuto por IP)** en los endpoints que procesan
archivos o escriben en la BBDD, usando `slowapi`. Protege tanto de un ataque
deliberado de fuerza bruta como de errores propios (por ejemplo, un bucle mal
hecho en el frontend que dispare cientos de peticiones seguidas).

**Nombres de archivo generados por el servidor, nunca por el cliente.** El
nombre con el que se guarda cada archivo en `uploads/` se construye a partir
del `id` interno (`watermarked_{track_id}_{recipient_id}_{code}.wav`), nunca
a partir del nombre que manda quien sube el archivo. Esto evita ataques de
*path traversal* (alguien mandando un nombre de archivo tipo
`../../etc/passwd` para intentar escribir fuera de la carpeta de subidas).

**Fallo seguro si falta configuración.** Si arrancas el servidor sin haber
definido `SECRET_KEY` en el `.env`, la API responde con error 500 en vez de
dejar los endpoints abiertos sin querer por un despiste de configuración.

**Descarga de archivos marcados solo vía endpoint autenticado.** La carpeta
`uploads/` no se sirve como estáticos (ni en el backend ni en el nginx del
frontend, que solo monta `frontend/`): la única forma de descargar una copia
marcada es `/watermarked-files/{id}/download`, protegido por sesión y
limitado a copias de tu propia cuenta.

**Chat de soporte con IA sin exponer secretos.** `/support-chat` sigue las
mismas reglas que el resto de la API (login, rate limiting) y usa
`ANTHROPIC_API_KEY` solo desde variables de entorno, nunca en el código. El
system prompt instruye explícitamente al modelo a no revelar claves, tokens
ni detalles internos de infraestructura, y si la clave no está configurada
el endpoint falla con un error controlado en vez de romper el servidor.

**Validación del contenido real del archivo subido.** `/watermark` y
`/verify` comprueban la cabecera RIFF/WAVE de los bytes recibidos, no solo
la extensión `.wav` del nombre de archivo — así un archivo renombrado con
otra extensión se rechaza con 400 antes de tocar disco. Si el archivo pasa
la cabecera pero el contenido está corrupto, el error también se controla
con un 400 en vez de un 500 (`backend/app/files.py`,
`validate_wav_signature`).

### Pendiente de securizar (para seguir mejorando)

- No hay HTTPS en local (en producción sí, terminado en el borde de
  Cloudflare por el Tunnel — ver "Despliegue y comunicación" en el Stack).
- El límite de rate limiting es por IP en memoria — en un despliegue con
  varias réplicas del backend, habría que centralizarlo (p.ej. con Redis).
- No hay verificación de email ni límite de intentos de login por cuenta
  (solo el rate limiting general por IP en `/auth/login`).
- El registro es público (cualquiera con el enlace puede crear una cuenta)
  — es la decisión tomada por ahora; si se quisiera cerrar, habría que
  añadir invitaciones o aprobación manual del admin.

La idea es completar cada pieza pendiente como commits separados (a poder ser,
pidiéndoselo a Claude conectado a este repo), para que el historial de commits
cuente la historia de cómo se construyó.

## Cómo arrancarlo en local

### Opción A — con Docker Compose (recomendada, ya probada)

```bash
cp .env.example .env
# Rellena SECRET_KEY en el .env, por ejemplo con:
#   openssl rand -hex 32
# ALLOWED_ORIGINS puede dejarse como "*" en local.
# Opcional: rellena ADMIN_EMAIL/ADMIN_PASSWORD para que esa cuenta se cree
# como admin al arrancar (si no, simplemente regístrate desde el dashboard).

docker-compose up -d --build
```

Esto levanta 3 servicios: `db` (PostgreSQL), `backend` (FastAPI en el puerto
`8000`) y `frontend` (nginx sirviendo el dashboard en el puerto `8080`).
Comprueba que los tres están arriba con `docker-compose ps`. Abre
http://localhost:8080 y regístrate desde la pantalla de login para acceder al
dashboard, o http://localhost:8000/docs para la API por Swagger.

### Opción B — backend suelto, sin Docker

```bash
cd backend
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# Define tu SECRET_KEY antes de arrancar (o cópiala en un .env, ver .env.example)
export SECRET_KEY="lo-que-tu-quieras"   # en Windows PowerShell: $env:SECRET_KEY="lo-que-tu-quieras"

uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs para probar los endpoints desde Swagger:
primero `POST /auth/register` (o `/auth/login`) para conseguir un
`access_token`, y luego pégalo en el botón "Authorize" de Swagger (como
`Bearer <token>`) para que se añada a las siguientes peticiones. Con esta
opción el frontend (`frontend/index.html`) hay que abrirlo suelto y
configurar la URL de la API desde su pantalla de "Cuenta".

## Probar el watermark por consola (sin la API)

```bash
cd backend
python -m app.watermark embed ejemplo.wav 42 ejemplo_marcado.wav
python -m app.watermark extract ejemplo_marcado.wav
```

## Siguientes pasos sugeridos

1. Repasa la sección "Pendiente de securizar" del README y ve tachando puntos.
2. Implementa un escáner automático que busque filtraciones periódicamente en
   fuentes externas (webs, foros) en vez de depender solo de la subida manual
   a `/verify`.
3. Cobro real (Stripe) para el plan "pro" — la columna `users.plan` y el
   rol admin ya están, falta la integración de pago en sí.

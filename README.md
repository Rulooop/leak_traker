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

## Stack tecnológico

**Backend**
- Python + FastAPI (framework de la API)
- SQLAlchemy (ORM para la base de datos)
- NumPy + SciPy (el watermark de audio, técnica FSK)
- slowapi (rate limiting), httpx (peticiones HTTP salientes)
- SQLite (desarrollo) / PostgreSQL (producción)

**Frontend**
- HTML, CSS y JavaScript puro (sin frameworks)
- Google Fonts: Space Grotesk, Inter, IBM Plex Mono
- SVG generado dinámicamente (la forma de onda del dashboard)

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
- [x] Modelo de datos (4 tablas)
- [x] Prototipo funcional de watermark inaudible (embed/extract con FSK en alta frecuencia)
- [x] API completa con FastAPI (watermark, verify, recipients, dashboard, descarga de archivos)
- [x] Autenticación por API key, límite de tamaño de archivo y rate limiting (ver "Seguridad" abajo)
- [x] Frontend propio (dashboard, alta de canciones, verificación, destinatarios, ajustes de conexión)
- [x] `docker-compose.yml` probado en local: los 3 servicios (`db`, `backend`, `frontend`) arrancan y responden correctamente
- [x] Alertas por Telegram probadas de verdad (bot propio, `sendMessage` vía API de Telegram) — ver `backend/app/routes/webhook.py`
- [x] Desplegado en internet: autoalojado desde la VM con Cloudflare Tunnel en `https://leaktracker.cloud`, con el túnel como servicio systemd persistente

## Seguridad

Decisiones de seguridad tomadas en este proyecto, y por qué:

**Autenticación por API key.** Todos los endpoints que crean o consultan datos
(`/watermark`, `/verify`, `/recipients`) exigen la cabecera `X-API-Key` con una
clave que se define en `.env` (nunca en el código, nunca en GitHub — está en
`.gitignore`). Sin esto, cualquiera que encontrara la URL del servidor podría
subir canciones o consultar destinatarios. La comparación de la clave usa
`secrets.compare_digest()` en vez de `==`, para evitar timing attacks (que
alguien pueda adivinar la clave carácter a carácter midiendo cuánto tarda en
responder el servidor).

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
definido `API_KEY` en el `.env`, la API responde con error 500 en vez de
dejar los endpoints abiertos sin querer por un despiste de configuración.

**Descarga de archivos marcados solo vía endpoint autenticado.** La carpeta
`uploads/` no se sirve como estáticos (ni en el backend ni en el nginx del
frontend, que solo monta `frontend/`): la única forma de descargar una copia
marcada es `/watermarked-files/{id}/download`, protegido con `X-API-Key`.

### Pendiente de securizar (para seguir mejorando)

- No hay HTTPS en local (en producción sí, terminado en el borde de
  Cloudflare por el Tunnel — ver "Despliegue y comunicación" en el Stack).
- No se valida el contenido real del archivo (solo la extensión `.wav`) —
  alguien podría subir un archivo con otra extensión renombrado a `.wav`.
  Se podría añadir una comprobación de las cabeceras reales del fichero.
- El límite de rate limiting es por IP en memoria — en un despliegue con
  varias réplicas del backend, habría que centralizarlo (p.ej. con Redis).

La idea es completar cada pieza pendiente como commits separados (a poder ser,
pidiéndoselo a Claude conectado a este repo), para que el historial de commits
cuente la historia de cómo se construyó.

## Cómo arrancarlo en local

### Opción A — con Docker Compose (recomendada, ya probada)

```bash
cp .env.example .env
# Rellena API_KEY en el .env, por ejemplo con:
#   openssl rand -hex 32
# ALLOWED_ORIGINS puede dejarse como "*" en local.

docker-compose up -d --build
```

Esto levanta 3 servicios: `db` (PostgreSQL), `backend` (FastAPI en el puerto
`8000`) y `frontend` (nginx sirviendo el dashboard en el puerto `8080`).
Comprueba que los tres están arriba con `docker-compose ps`. Abre
http://localhost:8080 para el dashboard y http://localhost:8000/docs para la
API por Swagger.

### Opción B — backend suelto, sin Docker

```bash
cd backend
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# Define tu API key antes de arrancar (o cópiala en un .env, ver .env.example)
export API_KEY="lo-que-tu-quieras"   # en Windows PowerShell: $env:API_KEY="lo-que-tu-quieras"

uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs para probar los endpoints desde Swagger — en
cada petición tendrás que añadir la cabecera `X-API-Key` con el valor que
hayas puesto arriba (Swagger tiene un botón "Authorize" para esto, o puedes
añadirla a mano en cada request). Con esta opción el frontend (`frontend/index.html`)
hay que abrirlo suelto y configurar la URL/API key desde su pantalla de "Ajustes".

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
3. Añade un login de verdad (usuario/contraseña o similar) para no tener que
   pegar la `API_KEY` a mano en los "Ajustes" del frontend cada vez.

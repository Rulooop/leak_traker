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
- [x] Autenticación por API key, límite de tamaño de archivo y rate limiting (ver "Seguridad" abajo)
- [ ] Webhook real hacia Slack/Telegram (hay un stub a completar)
- [ ] Frontend con más pulido visual
- [ ] Despliegue en Hetzner con Docker

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

### Pendiente de securizar (para seguir mejorando)

- Los archivos de audio en `uploads/` se sirven tal cual desde el sistema de
  ficheros si alguien conoce la ruta exacta — en producción convendría
  servirlos solo a través de un endpoint autenticado, no como estáticos.
- No hay HTTPS en local (sí en producción, vía Caddy/nginx delante).
- No se valida el contenido real del archivo (solo la extensión `.wav`) —
  alguien podría subir un archivo con otra extensión renombrado a `.wav`.
  Se podría añadir una comprobación de las cabeceras reales del fichero.
- El límite de rate limiting es por IP en memoria — en un despliegue con
  varias réplicas del backend, habría que centralizarlo (p.ej. con Redis).

La idea es completar cada pieza pendiente como commits separados (a poder ser,
pidiéndoselo a Claude conectado a este repo), para que el historial de commits
cuente la historia de cómo se construyó.

## Cómo arrancarlo en local

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
añadirla a mano en cada request).

## Probar el watermark por consola (sin la API)

```bash
cd backend
python -m app.watermark embed ejemplo.wav 42 ejemplo_marcado.wav
python -m app.watermark extract ejemplo_marcado.wav
```

## Siguientes pasos sugeridos

1. Completa `backend/app/routes/webhook.py` para que avise de verdad (Slack/Telegram).
2. Cambia SQLite por PostgreSQL en `docker-compose.yml` para producción (ya está
   preparado el `docker-compose.yml`, solo falta probarlo).
3. Pule el frontend (ahora mismo es solo un panel funcional, sin mucho diseño).
4. Despliega en un VPS de Hetzner con `docker-compose up -d` detrás de Caddy/nginx.
5. Repasa la sección "Pendiente de securizar" del README y ve tachando puntos.

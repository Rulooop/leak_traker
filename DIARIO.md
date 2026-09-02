# Diario de desarrollo — Leak Tracker

Registro cronológico de cómo se construyó el proyecto, sesión a sesión. El
historial de commits en GitHub tiene el detalle técnico línea por línea; este
diario es el resumen en lenguaje normal de qué se hizo y por qué en cada
sesión de trabajo.

---

## 14 de agosto — Arranque del proyecto

**Idea y arquitectura.** Definí el concepto: un sistema que incrusta una
marca de agua inaudible en las canciones antes de enviarlas a colaboradores,
para poder identificar el origen si se filtran. Diseñé la arquitectura
completa (BBDD + API/webhook + aplicación + GitHub), tal y como pedía el
enunciado del trabajo.

**Backend inicial.** Construí las 4 tablas de la base de datos (canciones,
destinatarios, copias marcadas, filtraciones detectadas), el prototipo de
watermark en Python (técnica FSK en alta frecuencia), y la API mínima con
FastAPI (`/watermark`, `/verify`, `/recipients`).

**Entorno de trabajo.** Monté una máquina virtual con Ubuntu 24.04 en
VirtualBox, instalé Git, Python y Docker, creé el repositorio en GitHub
(`Rulooop/leak_traker`) y subí el primer commit: *"esqueleto inicial"*.

---

## 15 de agosto — Seguridad

**Medidas de seguridad implementadas y probadas:**
- Autenticación por API key (cabecera `X-API-Key`), con comparación segura
  contra timing attacks.
- Límite de tamaño de archivo (50MB), cortando la subida antes de escribir a
  disco.
- Rate limiting (10 peticiones/minuto por IP) en los endpoints sensibles.
- Nombres de archivo generados por el servidor, nunca por el cliente
  (protección contra path traversal).
- Fallo seguro si falta la `API_KEY` en la configuración.

Cada medida se probó activamente lanzando el servidor y comprobando
respuestas reales (401 sin clave, 413 con archivo demasiado grande, etc.),
no solo se escribió el código. Documenté todo en el README, en una sección
de "Seguridad" con las decisiones y el porqué de cada una.

**Entorno.** Instalé Claude Code en la VM para poder acelerar el resto del
desarrollo más adelante.

---

## 26 de agosto — Interfaz web y cierre

**Frontend real.** Diseñé y construí una interfaz propia de una sola página:
sidebar de navegación (Dashboard, Nueva canción, Verificar filtración,
Destinatarios, Ajustes), con identidad visual propia (paleta oscura con
acento ámbar, tipografías Space Grotesk/Inter/IBM Plex Mono, y una forma de
onda ilustrativa marcando la "zona de watermark" como elemento visual
característico).

**Backend ampliado.** Añadí los endpoints que le faltaban a la API para
alimentar el dashboard (`/stats`, `/tracks`, `/watermarked-files`,
`/leak-detections`) y un endpoint de descarga de archivos marcados.

**Bug encontrado y corregido.** El frontend no conseguía conectar con la API
por un conflicto de configuración CORS (`allow_credentials=True` combinado
con `allow_origins="*"`, que los navegadores bloquean). Se corrigió a
`allow_credentials=False`, ya que la autenticación se hace por cabecera
`X-API-Key`, no por cookies.

**Claude Code operativo.** Cargué saldo en la cuenta y seleccioné el modelo
Sonnet (más eficiente en coste que el modelo por defecto) para completar
desde la propia VM las piezas que aún quedan pendientes: el webhook real y
el despliegue en producción.

---

## 26 de agosto — Entorno local y fix de descargas

**Entorno con Docker.** Creé el `.env` local a partir de `.env.example`, con
una `API_KEY` generada con `openssl rand -hex 32` y `ALLOWED_ORIGINS=*`, y
levanté los 3 servicios (`db`, `backend`, `frontend`) con `docker-compose up
-d`, comprobando que los tres arrancan bien y responden correctamente.

**Audio de prueba.** Generé un `ejemplo.wav` (mono, 44.1kHz, 5 segundos, tono
de 440Hz) por consola para poder probar el flujo de watermark/verify a mano.
No se sube al repo — es solo un archivo de prueba local, no forma parte del
proyecto.

**Bug de descarga corregido.** Los enlaces "Descargar" del archivo marcado
(en el dashboard y tras generar una copia nueva) eran `<a href="...">`
normales, así que el navegador no mandaba la cabecera `X-API-Key` al pedir
`/watermarked-files/{id}/download`, y la API respondía 401. Se sustituyeron
por botones que llaman a una función `downloadWatermarkedFile()`: hace el
`fetch` autenticado con la función `api()` ya existente, convierte la
respuesta en `blob` y fuerza la descarga con un enlace temporal generado con
`URL.createObjectURL()`.

**Verificación de la API key.** Confirmé que la API rechaza la clave antigua
(401) y acepta solo la nueva generada con `openssl rand -hex 32`.

---

## 1 de septiembre — Alertas de Telegram conectadas

**Reinstalación de Claude Code.** Tuve que reinstalar Claude Code tras un
fallo antes de empezar la sesión.

**Webhook real conectado.** Creé un bot de Telegram (@Trackerleakbot) con
@BotFather y sustituí el webhook genérico por una llamada directa a la API
de Telegram (`sendMessage`). El token y el `chat_id` viven en `.env`, no en
el código.

**Prueba end-to-end confirmada.** Probé el flujo completo dos veces: primero
con `/webhook-test`, luego con un caso real (crear destinatario → generar
copia marcada → "filtrarla" descargándola → subirla a `/verify`). En ambos
casos la alerta llegó sola a Telegram al detectar la filtración, sin
intervención manual.

**Escáner automático, aplazado.** Decidí dejar como mejora futura (anotada
en el README) un escáner que busque filtraciones periódicamente en fuentes
externas (webs, foros), en vez de depender solo de la subida manual a
`/verify`.

---

## 2 de septiembre — Rotación de claves

**API_KEY y token de Telegram rotados.** Al quedar expuestas ambas claves,
generé una `API_KEY` nueva (`openssl rand -hex 32`) y revoqué el token del
bot de Telegram desde @BotFather, sustituyéndolo por uno nuevo. Actualicé
`.env` y recreé el contenedor del backend (con este docker-compose v1, un
simple `restart` no relee el `.env`; hace falta `stop` + `rm -f` + `up -d`).

**Verificación.** Confirmé que la API rechaza la clave vieja (401) y acepta
la nueva, y que el bot de Telegram sigue funcionando con el token nuevo
(alerta de prueba recibida correctamente).

---

## 2 de septiembre — Despliegue en internet con Cloudflare Tunnel

**Autoalojado en vez de VPS de pago.** Descarté Hetzner (de pago) y decidí
publicar el proyecto directamente desde la propia VM usando Cloudflare
Tunnel, sin gastar en un VPS.

**Dominio y DNS.** Compré `leaktracker.cloud` en IONOS (0,50€ el primer año),
lo conecté a Cloudflare y cambié los nameservers en IONOS a los de
Cloudflare. Al crear las rutas DNS hubo un conflicto: unos registros A/AAAA
antiguos de la página de aparcamiento de IONOS ocupaban ya el nombre
`leaktracker.cloud`, y un CNAME no puede coexistir con otros registros para
el mismo nombre. Los borré en Cloudflare y las rutas se crearon bien.

**Túnel configurado.** Instalé `cloudflared` en la VM, lo autentiqué con mi
cuenta de Cloudflare y creé un túnel con nombre fijo (`leak-tracker`) en vez
de uno rápido con URL aleatoria, con dos rutas:
`leaktracker.cloud` → frontend (`localhost:8080`) y
`api.leaktracker.cloud` → backend (`localhost:8000`).

**Confirmado accesible desde fuera.** Probé la web desde el móvil con datos
móviles (no wifi): `https://leaktracker.cloud` responde de verdad desde
internet.

**Túnel persistente.** Instalé `cloudflared` como servicio systemd para que
sobreviva a cerrar la terminal o reiniciar la VM. El primer intento falló
porque `sudo` busca la configuración en `/root` en vez de en mi carpeta
personal; lo arreglé indicando la ruta completa con `--config`. El servicio
quedó `enabled` y `active (running)`.

**Aviso importante.** La web solo está disponible mientras la VM esté
encendida y corriendo — el servicio systemd la hace sobrevivir a cerrar la
terminal o a un reinicio de la VM, pero no a apagar la VM o el ordenador.

**CORS restringido.** Con la web ya pública de verdad, cambié
`ALLOWED_ORIGINS` de `*` a `https://leaktracker.cloud` en el `.env` de la VM
y recreé el contenedor del backend para que cogiera el cambio.

## Pendiente para la próxima sesión

- Revisar los puntos de la lista "Pendiente de securizar" del README.
- Implementar el escáner automático de filtraciones en fuentes externas.
- Añadir un login de verdad al frontend, para no depender de pegar la
  `API_KEY` a mano en "Ajustes".

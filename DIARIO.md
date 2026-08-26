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

## Pendiente para la próxima sesión

- Conectar el webhook real a Slack/Telegram.
- Desplegar en un VPS de Hetzner con el `docker-compose.yml` ya preparado.
- Revisar los puntos de la lista "Pendiente de securizar" del README.

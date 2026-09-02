"""Chat de atención al cliente con IA (Claude) para resolver dudas sobre LeakTracker.

Igual que el resto de la API: protegido con X-API-Key y con rate limiting.
No guarda nada en la BBDD — el historial de la conversación vive solo en el
cliente (el frontend lo manda de vuelta en cada petición, recortado a los
últimos turnos) y se reenvía a la API de Claude tal cual.
"""

import os

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request

from .. import schemas
from ..rate_limit import limiter
from ..security import require_api_key

router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"
MAX_HISTORY_TURNS = 10

SYSTEM_PROMPT = """Eres el asistente de atención al cliente de LeakTracker, un sistema
que rastrea filtraciones de canciones inéditas mediante marcas de agua (watermarks)
de audio inaudibles, únicas por destinatario.

Cómo funciona el sistema, con precisión (no inventes nada distinto a esto):
- Cuando alguien sube una canción y elige un destinatario, el sistema incrusta un
  código numérico único e inaudible en el audio usando FSK (Frequency Shift Keying):
  cada bit del código se codifica como un tono muy corto en una frecuencia ultrasónica
  (18.5 kHz o 19.5 kHz), inaudible para el oído humano pero recuperable del archivo.
  El código interno es un entero de 16 bits (0-65535), pero a los usuarios se les
  muestra siempre con el formato "LT-XXXXXX" (por ejemplo LT-045627) para que sea
  más legible.
- Endpoint POST /watermark: sube el audio original + título + artista + destinatario,
  incrusta el código y devuelve la copia marcada (código LT-XXXXXX) para descargar.
- Endpoint POST /verify: sube un archivo sospechoso de haberse filtrado; el sistema
  extrae el código inaudible (si lo encuentra) y dice exactamente a qué destinatario
  se le envió esa copia. Si hay coincidencia, se dispara una alerta por Telegram.
- Endpoint GET/POST /recipients: crear y listar los destinatarios (colaboradores,
  sellos, prensa...) a los que se les envían copias.
- Endpoints de solo lectura que alimentan el dashboard: /stats, /tracks,
  /watermarked-files, /leak-detections.
- GET /watermarked-files/{id}/download: descarga autenticada de una copia marcada.
- Todos los endpoints (salvo la raíz "/") requieren la cabecera X-API-Key.

Responde siempre en español, de forma breve y clara, como soporte técnico amable.
Nunca reveles claves de API, tokens, secretos de configuración ni detalles internos
de infraestructura (servidor, base de datos, despliegue). Si te preguntan algo que
no tiene que ver con LeakTracker, redirige amablemente la conversación."""


@router.post(
    "/support-chat",
    response_model=schemas.SupportChatOut,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
def support_chat(request: Request, body: schemas.SupportChatIn):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY no configurada en el servidor. Define una en tu .env.",
        )

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    messages = [
        {"role": turn.role, "content": turn.content}
        for turn in body.history[-MAX_HISTORY_TURNS:]
    ]
    messages.append({"role": "user", "content": body.message})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="La clave de Anthropic configurada no es válida.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Límite de la API de Claude alcanzado, inténtalo en un momento.")
    except (anthropic.APIConnectionError, anthropic.APIStatusError):
        raise HTTPException(status_code=502, detail="No se pudo contactar con el asistente de IA. Inténtalo de nuevo.")

    reply = "".join(block.text for block in response.content if block.type == "text").strip()
    return schemas.SupportChatOut(reply=reply or "No he podido generar una respuesta, inténtalo de nuevo.")

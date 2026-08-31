"""
Envío de alertas cuando se detecta una filtración, vía bot de Telegram.
"""

import os

import httpx
from fastapi import APIRouter

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_alert(message: str) -> bool:
    """Envía 'message' al chat de Telegram configurado. Devuelve True si se envió correctamente."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[ALERTA - Telegram sin configurar] {message}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=5.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        print(f"[ALERTA] Error enviando mensaje a Telegram: {exc}")
        return False


@router.post("/webhook-test")
def test_webhook():
    """Endpoint de prueba para disparar una alerta manualmente."""
    sent = send_alert("🔔 Alerta de prueba desde Leak Tracker")
    return {"sent": sent}

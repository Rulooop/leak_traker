"""
Envío de alertas cuando se detecta una filtración.

Esto es un STUB a propósito: aquí es donde tienes que enganchar Slack,
Telegram, Discord o lo que prefieras. Déjaselo a Claude como una tarea
concreta: "completa send_alert() para que mande un mensaje a mi canal de
Slack usando un webhook incoming", por ejemplo.
"""

import os

import httpx
from fastapi import APIRouter

router = APIRouter()

WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")  # p.ej. un Incoming Webhook de Slack


def send_alert(message: str) -> bool:
    """Envía 'message' al webhook configurado. Devuelve True si se envió correctamente."""
    if not WEBHOOK_URL:
        print(f"[ALERTA - sin webhook configurado] {message}")
        return False

    try:
        response = httpx.post(WEBHOOK_URL, json={"text": message}, timeout=5.0)
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        print(f"[ALERTA] Error enviando webhook: {exc}")
        return False


@router.post("/webhook-test")
def test_webhook():
    """Endpoint de prueba para disparar una alerta manualmente."""
    sent = send_alert("🔔 Alerta de prueba desde Leak Tracker")
    return {"sent": sent}

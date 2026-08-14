"""
Autenticación sencilla mediante API key.

Cualquier request a un endpoint protegido debe incluir la cabecera:
    X-API-Key: <tu-clave-secreta>

La clave se define en la variable de entorno API_KEY (ver .env.example).
Esto NO es un sistema de usuarios completo (no hay login, ni roles) —
es la protección mínima razonable para que esta API no quede abierta a
cualquiera que encuentre la URL. Para un proyecto más grande, lo suyo
sería pasar a JWT con usuarios reales.
"""

import os
import secrets

from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY")


def require_api_key(x_api_key: str = Header(default=None)) -> None:
    if not API_KEY:
        # Si no se ha configurado ninguna API_KEY en el .env, bloqueamos por
        # defecto en vez de dejar la API abierta sin querer.
        raise HTTPException(
            status_code=500,
            detail="API_KEY no configurada en el servidor. Define una en tu .env.",
        )

    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="API key inválida o ausente (cabecera X-API-Key).")

"""Autenticación real de usuarios: contraseñas hasheadas (bcrypt) + sesión
mediante JWT firmado. Sustituye a la antigua API_KEY estática compartida.

Flujo: POST /auth/register o /auth/login devuelven un access_token (JWT) que
el frontend guarda y manda como cabecera `Authorization: Bearer <token>` en
cada petición. `get_current_user` valida ese token y carga al usuario real
desde la BBDD; `require_admin` además exige que sea un administrador.
"""

import datetime
import os

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 7  # una semana


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _require_secret_key() -> str:
    if not SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="SECRET_KEY no configurada en el servidor. Define una en tu .env.",
        )
    return SECRET_KEY


def create_access_token(user_id: int) -> str:
    secret = _require_secret_key()
    payload = {
        "sub": str(user_id),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def get_current_user(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    secret = _require_secret_key()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sesión no válida. Inicia sesión de nuevo.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Sesión no válida o caducada. Inicia sesión de nuevo.")

    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión no válida. Inicia sesión de nuevo.")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != models.ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Solo un administrador puede hacer esto.")
    return user

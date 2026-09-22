"""Tareas mínimas de arranque para el login real.

Este proyecto no usa Alembic, así que los cambios de esquema que llegan
después de la primera versión de la BBDD (aquí: la columna `owner_id` en
`tracks`/`recipients`, que no existía antes del login) se aplican a mano con
ALTER TABLE, ignorando el error si la columna ya existe. En una BBDD nueva,
`Base.metadata.create_all()` ya crea las tablas con la columna incluida, así
que el ALTER simplemente falla y no hace nada.

También siembra (o promociona) la cuenta admin definida en
ADMIN_EMAIL/ADMIN_PASSWORD, y le asigna las canciones/destinatarios que se
crearon antes de que existiera el login (que se quedaron sin dueño).
"""

import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from . import models
from .auth import hash_password
from .database import SessionLocal

_SCHEMA_MIGRATIONS = [
    "ALTER TABLE tracks ADD COLUMN owner_id INTEGER REFERENCES users(id)",
    "ALTER TABLE recipients ADD COLUMN owner_id INTEGER REFERENCES users(id)",
]


def _apply_schema_migrations(engine) -> None:
    for statement in _SCHEMA_MIGRATIONS:
        try:
            with engine.begin() as conn:
                conn.execute(text(statement))
        except (OperationalError, ProgrammingError):
            pass  # la columna ya existe


def _seed_admin_user(db) -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    if not admin_email:
        return
    admin_email = admin_email.lower()

    admin = db.query(models.User).filter_by(email=admin_email).first()
    if not admin:
        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            return
        admin = models.User(
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=models.ROLE_ADMIN,
            plan=models.PLAN_PRO,
        )
        db.add(admin)
        db.flush()
    elif admin.role != models.ROLE_ADMIN:
        admin.role = models.ROLE_ADMIN

    db.query(models.Track).filter(models.Track.owner_id.is_(None)).update(
        {"owner_id": admin.id}, synchronize_session=False
    )
    db.query(models.Recipient).filter(models.Recipient.owner_id.is_(None)).update(
        {"owner_id": admin.id}, synchronize_session=False
    )
    db.commit()


def run_startup_tasks(engine) -> None:
    _apply_schema_migrations(engine)
    db = SessionLocal()
    try:
        _seed_admin_user(db)
    finally:
        db.close()

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# En local usamos SQLite para no complicarnos.
# En producción, cambia esto por una URL de PostgreSQL, p.ej:
# postgresql+psycopg2://user:password@db:5432/leaktracker
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leaktracker.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency de FastAPI: abre una sesión de BBDD y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

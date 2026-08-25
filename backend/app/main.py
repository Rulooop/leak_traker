import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .rate_limit import limiter
from .routes import dashboard, verify, watermark, webhook
from .security import require_api_key

# Crea las tablas si no existen (para producción real, mejor usar Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Leak Tracker API",
    description="Rastrea filtraciones de música mediante watermarks de audio inaudibles.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# En dev dejamos cualquier origen. En producción, define ALLOWED_ORIGINS en tu
# .env con la URL real de tu web (p.ej. "https://tuweb.com"), separadas por
# comas si necesitas más de una.
# Nota: allow_credentials=False porque no usamos cookies de sesión, solo la
# cabecera X-API-Key — así podemos combinar "*" con cualquier origen sin que
# el navegador lo bloquee (los navegadores prohíben "*" + credentials=True).
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watermark.router, tags=["watermark"])
app.include_router(verify.router, tags=["verify"])
app.include_router(webhook.router, tags=["webhook"])
app.include_router(dashboard.router, tags=["dashboard"])


@app.get("/")
def root():
    return {"status": "ok", "service": "leak-tracker"}


@app.post(
    "/recipients",
    response_model=schemas.RecipientOut,
    tags=["recipients"],
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
def create_recipient(request: Request, recipient: schemas.RecipientCreate, db: Session = Depends(get_db)):
    db_recipient = models.Recipient(**recipient.model_dump())
    db.add(db_recipient)
    db.commit()
    db.refresh(db_recipient)
    return db_recipient


@app.get(
    "/recipients",
    response_model=list[schemas.RecipientOut],
    tags=["recipients"],
    dependencies=[Depends(require_api_key)],
)
def list_recipients(db: Session = Depends(get_db)):
    return db.query(models.Recipient).all()

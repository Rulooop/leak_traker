"""Endpoints de solo lectura que alimentan el dashboard del frontend.

Todos protegidos con API key, igual que el resto de la API — estos datos
(quién recibió qué copia, qué filtraciones se han detectado) son sensibles.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    return schemas.StatsOut(
        total_tracks=db.query(models.Track).count(),
        total_recipients=db.query(models.Recipient).count(),
        total_watermarked_files=db.query(models.WatermarkedFile).count(),
        total_leaks_detected=db.query(models.LeakDetection).filter_by(matched=1).count(),
    )


@router.get("/tracks", response_model=list[schemas.TrackOut])
def list_tracks(db: Session = Depends(get_db)):
    return db.query(models.Track).order_by(models.Track.created_at.desc()).all()


@router.get("/watermarked-files", response_model=list[schemas.WatermarkedFileDetailOut])
def list_watermarked_files(db: Session = Depends(get_db)):
    files = (
        db.query(models.WatermarkedFile)
        .order_by(models.WatermarkedFile.created_at.desc())
        .all()
    )
    return [
        schemas.WatermarkedFileDetailOut(
            id=f.id,
            code=f.code,
            created_at=f.created_at,
            track_title=f.track.title,
            recipient_name=f.recipient.name,
        )
        for f in files
    ]


@router.get("/leak-detections", response_model=list[schemas.LeakDetectionOut])
def list_leak_detections(db: Session = Depends(get_db)):
    detections = (
        db.query(models.LeakDetection)
        .order_by(models.LeakDetection.created_at.desc())
        .all()
    )
    return [
        schemas.LeakDetectionOut(
            id=d.id,
            extracted_code=d.extracted_code,
            matched=bool(d.matched),
            source_note=d.source_note,
            created_at=d.created_at,
            track_title=d.watermarked_file.track.title if d.watermarked_file else None,
            recipient_name=d.watermarked_file.recipient.name if d.watermarked_file else None,
        )
        for d in detections
    ]

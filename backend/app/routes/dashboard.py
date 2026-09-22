"""Endpoints de solo lectura que alimentan el dashboard del frontend.

Todos requieren sesión (login). Un usuario normal solo ve sus propios datos
(sus canciones, destinatarios, copias marcadas y filtraciones); un admin ve
los de todo el mundo — ver `models.ROLE_ADMIN`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(dependencies=[Depends(get_current_user)])


def _scope_by_track_owner(query, user: models.User):
    """Filtra una query que ya hace JOIN con Track por su owner_id, salvo para admin."""
    if user.role == models.ROLE_ADMIN:
        return query
    return query.filter(models.Track.owner_id == user.id)


def _scope_recipients(query, user: models.User):
    if user.role == models.ROLE_ADMIN:
        return query
    return query.filter(models.Recipient.owner_id == user.id)


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    watermarked_files = _scope_by_track_owner(
        db.query(models.WatermarkedFile).join(models.Track), user
    )
    leak_detections = _scope_by_track_owner(
        db.query(models.LeakDetection)
        .join(models.WatermarkedFile)
        .join(models.Track)
        .filter(models.LeakDetection.matched == 1),
        user,
    )
    return schemas.StatsOut(
        total_tracks=_scope_by_track_owner(db.query(models.Track), user).count(),
        total_recipients=_scope_recipients(db.query(models.Recipient), user).count(),
        total_watermarked_files=watermarked_files.count(),
        total_leaks_detected=leak_detections.count(),
    )


@router.get("/tracks", response_model=list[schemas.TrackOut])
def list_tracks(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = _scope_by_track_owner(db.query(models.Track), user)
    return query.order_by(models.Track.created_at.desc()).all()


@router.get("/watermarked-files", response_model=list[schemas.WatermarkedFileDetailOut])
def list_watermarked_files(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = _scope_by_track_owner(db.query(models.WatermarkedFile).join(models.Track), user)
    files = query.order_by(models.WatermarkedFile.created_at.desc()).all()
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
def list_leak_detections(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    query = db.query(models.LeakDetection)
    if user.role == models.ROLE_ADMIN:
        query = query.outerjoin(models.WatermarkedFile).outerjoin(models.Track)
    else:
        # Un usuario normal solo ve las detecciones que apuntan a una de sus
        # propias canciones — las que no encontraron ningún match no están
        # ligadas a ningún dueño, así que solo las ve el admin.
        query = query.join(models.WatermarkedFile).join(models.Track).filter(
            models.Track.owner_id == user.id
        )
    detections = query.order_by(models.LeakDetection.created_at.desc()).all()
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

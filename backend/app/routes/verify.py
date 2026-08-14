import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..watermark import extract_watermark
from .webhook import send_alert

router = APIRouter()


@router.post("/verify", response_model=schemas.VerifyResult)
async def verify_suspect_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        extracted_code = extract_watermark(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)

    watermarked_file = None
    if extracted_code is not None:
        watermarked_file = (
            db.query(models.WatermarkedFile).filter_by(code=extracted_code).first()
        )

    detection = models.LeakDetection(
        watermarked_file_id=watermarked_file.id if watermarked_file else None,
        extracted_code=extracted_code,
        matched=1 if watermarked_file else 0,
        source_note="Subido manualmente vía /verify",
    )
    db.add(detection)
    db.commit()

    if watermarked_file:
        message = (
            f"🚨 Filtración detectada: '{watermarked_file.track.title}' "
            f"viene de {watermarked_file.recipient.name} (código {extracted_code})"
        )
        send_alert(message)
        return schemas.VerifyResult(
            matched=True,
            extracted_code=extracted_code,
            recipient_name=watermarked_file.recipient.name,
            track_title=watermarked_file.track.title,
            message=message,
        )

    return schemas.VerifyResult(
        matched=False,
        extracted_code=extracted_code,
        message="No se encontró ningún watermark conocido en este archivo.",
    )

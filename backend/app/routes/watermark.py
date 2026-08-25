import random
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..files import read_and_check_size
from ..rate_limit import limiter
from ..security import require_api_key
from ..watermark import embed_watermark

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _generate_unique_code(db: Session) -> int:
    """Genera un código de 16 bits que no exista todavía en la BBDD."""
    for _ in range(100):
        code = random.randint(0, 2 ** 16 - 1)
        exists = db.query(models.WatermarkedFile).filter_by(code=code).first()
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="No se pudo generar un código único, inténtalo de nuevo.")


@router.post("/watermark", response_model=schemas.WatermarkedFileOut, dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def create_watermarked_file(
    request: Request,
    title: str = Form(...),
    artist: str = Form(...),
    recipient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    recipient = db.query(models.Recipient).get(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Destinatario no encontrado. Créalo primero en /recipients.")

    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Por ahora solo se admiten archivos .wav")

    file_bytes = await read_and_check_size(file)

    track = models.Track(title=title, artist=artist)
    db.add(track)
    db.flush()  # para obtener track.id sin hacer commit todavía

    # El nombre del archivo lo generamos NOSOTROS a partir del id — nunca usamos
    # el nombre que manda el cliente, así evitamos problemas de path traversal
    # (alguien mandando un filename tipo "../../etc/passwd").
    input_path = UPLOAD_DIR / f"original_{track.id}.wav"
    input_path.write_bytes(file_bytes)

    code = _generate_unique_code(db)
    output_path = UPLOAD_DIR / f"watermarked_{track.id}_{recipient_id}_{code}.wav"

    embed_watermark(str(input_path), code, str(output_path))

    watermarked_file = models.WatermarkedFile(
        track_id=track.id,
        recipient_id=recipient_id,
        code=code,
        file_path=str(output_path),
    )
    db.add(watermarked_file)
    db.commit()
    db.refresh(watermarked_file)

    return watermarked_file


@router.get("/watermarked-files/{file_id}/download", dependencies=[Depends(require_api_key)])
def download_watermarked_file(file_id: int, db: Session = Depends(get_db)):
    watermarked_file = db.query(models.WatermarkedFile).get(file_id)
    if not watermarked_file:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    path = Path(watermarked_file.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el servidor.")

    return FileResponse(
        path,
        media_type="audio/wav",
        filename=f"{watermarked_file.track.title}_{watermarked_file.recipient.name}.wav",
    )

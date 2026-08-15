"""Utilidades compartidas para manejar archivos subidos de forma segura."""

from fastapi import HTTPException, UploadFile

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


async def read_and_check_size(file: UploadFile, max_size: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """Lee el archivo entero comprobando que no supere max_size, para evitar que
    alguien intente tumbar el servicio subiendo un archivo enorme."""
    chunks = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Archivo demasiado grande (máximo {max_size // (1024*1024)}MB).",
            )
        chunks.append(chunk)
    return b"".join(chunks)

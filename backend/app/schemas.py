import datetime

from pydantic import BaseModel


class RecipientCreate(BaseModel):
    name: str
    email: str | None = None
    notes: str | None = None


class RecipientOut(RecipientCreate):
    id: int

    class Config:
        from_attributes = True


class WatermarkedFileOut(BaseModel):
    id: int
    track_id: int
    recipient_id: int
    code: int
    file_path: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class VerifyResult(BaseModel):
    matched: bool
    extracted_code: int | None
    recipient_name: str | None = None
    track_title: str | None = None
    message: str

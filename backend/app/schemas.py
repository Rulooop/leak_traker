import datetime
from typing import Literal

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


class TrackOut(BaseModel):
    id: int
    title: str
    artist: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class WatermarkedFileDetailOut(BaseModel):
    id: int
    code: int
    created_at: datetime.datetime
    track_title: str
    recipient_name: str


class LeakDetectionOut(BaseModel):
    id: int
    extracted_code: int | None
    matched: bool
    source_note: str | None
    created_at: datetime.datetime
    track_title: str | None = None
    recipient_name: str | None = None


class StatsOut(BaseModel):
    total_tracks: int
    total_recipients: int
    total_watermarked_files: int
    total_leaks_detected: int


class SupportChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SupportChatIn(BaseModel):
    message: str
    history: list[SupportChatTurn] = []


class SupportChatOut(BaseModel):
    reply: str

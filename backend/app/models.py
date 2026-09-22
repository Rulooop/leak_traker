import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

ROLE_ADMIN = "admin"
ROLE_USER = "user"

PLAN_FREE = "free"
PLAN_PRO = "pro"


class User(Base):
    """Cuenta de acceso al dashboard. `role` distingue admin de usuario normal,
    `plan` es la base para limitar uso por cuenta cuando se implemente el cobro."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=ROLE_USER)
    plan = Column(String, nullable=False, default=PLAN_FREE)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tracks = relationship("Track", back_populates="owner")
    recipients = relationship("Recipient", back_populates="owner")


class Track(Base):
    """Una canción original subida al sistema."""

    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="tracks")
    watermarked_files = relationship("WatermarkedFile", back_populates="track")


class Recipient(Base):
    """Alguien a quien se le envía una copia (colaborador, sello, prensa...)."""

    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="recipients")
    watermarked_files = relationship("WatermarkedFile", back_populates="recipient")


class WatermarkedFile(Base):
    """Registro de cada copia marcada: qué código se le puso y a quién."""

    __tablename__ = "watermarked_files"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    code = Column(Integer, nullable=False, unique=True, index=True)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    track = relationship("Track", back_populates="watermarked_files")
    recipient = relationship("Recipient", back_populates="watermarked_files")
    detections = relationship("LeakDetection", back_populates="watermarked_file")


class LeakDetection(Base):
    """Cada vez que se sube un archivo sospechoso y se extrae un código."""

    __tablename__ = "leak_detections"

    id = Column(Integer, primary_key=True, index=True)
    watermarked_file_id = Column(Integer, ForeignKey("watermarked_files.id"), nullable=True)
    extracted_code = Column(Integer, nullable=True)
    source_note = Column(String, nullable=True)  # dónde se encontró / quién lo subió
    matched = Column(Integer, default=0)  # 0 = sin match, 1 = match encontrado
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    watermarked_file = relationship("WatermarkedFile", back_populates="detections")

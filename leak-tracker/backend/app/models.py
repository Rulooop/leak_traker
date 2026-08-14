import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Track(Base):
    """Una canción original subida al sistema."""

    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    watermarked_files = relationship("WatermarkedFile", back_populates="track")


class Recipient(Base):
    """Alguien a quien se le envía una copia (colaborador, sello, prensa...)."""

    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)

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

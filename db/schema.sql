-- Schema de referencia (equivalente a los modelos de SQLAlchemy en backend/app/models.py).
-- SQLAlchemy crea estas tablas automáticamente al arrancar la app, pero tener el
-- SQL a mano ayuda a documentar la BBDD como entregable independiente.

CREATE TABLE tracks (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR NOT NULL,
    artist      VARCHAR NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE recipients (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR NOT NULL,
    email   VARCHAR,
    notes   VARCHAR
);

CREATE TABLE watermarked_files (
    id            SERIAL PRIMARY KEY,
    track_id      INTEGER NOT NULL REFERENCES tracks(id),
    recipient_id  INTEGER NOT NULL REFERENCES recipients(id),
    code          INTEGER NOT NULL UNIQUE,
    file_path     VARCHAR NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE leak_detections (
    id                    SERIAL PRIMARY KEY,
    watermarked_file_id   INTEGER REFERENCES watermarked_files(id),
    extracted_code        INTEGER,
    source_note           VARCHAR,
    matched               INTEGER NOT NULL DEFAULT 0,
    created_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_watermarked_files_code ON watermarked_files(code);

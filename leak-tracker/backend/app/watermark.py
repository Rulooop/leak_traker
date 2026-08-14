"""
Prototipo de watermark de audio inaudible.

Técnica: FSK (Frequency Shift Keying) en alta frecuencia.
Codificamos el "code" (un entero) en binario de longitud fija. Cada bit se
representa como un tono corto: FREQ_0 si el bit es 0, FREQ_1 si el bit es 1.
Esos tonos van en frecuencias muy altas (18-20 kHz), donde el oído humano
apenas percibe nada pero un micrófono/archivo digital normal sí las captura.

Esto es un PROTOTIPO para demostrar el concepto, no una técnica de
watermarking robusta a nivel industrial (eso usaría spread-spectrum,
psychoacoustic masking, etc.). Para el trabajo es más que suficiente: se
puede incrustar un código y recuperarlo del mismo archivo (o de una copia
sin recomprimir agresivamente).

Uso por consola:
    python -m app.watermark embed entrada.wav 42 salida.wav
    python -m app.watermark extract salida.wav
"""

import sys

import numpy as np
from scipy.io import wavfile

FREQ_0 = 18500  # Hz -> representa el bit 0
FREQ_1 = 19500  # Hz -> representa el bit 1
BIT_DURATION = 0.08  # segundos por bit
CODE_BITS = 16  # nº de bits del código -> soporta códigos de 0 a 65535
AMPLITUDE = 0.02  # amplitud del tono insertado (bajo, para que sea inaudible)


def _int_to_bits(code: int, n_bits: int = CODE_BITS) -> str:
    if code < 0 or code >= 2 ** n_bits:
        raise ValueError(f"El código debe estar entre 0 y {2 ** n_bits - 1}")
    return format(code, f"0{n_bits}b")


def _bits_to_int(bits: str) -> int:
    return int(bits, 2)


def embed_watermark(input_path: str, code: int, output_path: str) -> None:
    """Incrusta 'code' en el audio de input_path y guarda el resultado en output_path."""
    sample_rate, audio = wavfile.read(input_path)

    # Trabajamos en mono y float para no perder precisión al sumar el tono.
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    original_dtype = audio.dtype
    audio = audio.astype(np.float64)

    bits = _int_to_bits(code)
    bit_samples = int(BIT_DURATION * sample_rate)
    max_amplitude = np.iinfo(original_dtype).max if np.issubdtype(original_dtype, np.integer) else 1.0

    watermark_signal = np.zeros(bit_samples * len(bits))
    t = np.arange(bit_samples) / sample_rate

    for i, bit in enumerate(bits):
        freq = FREQ_1 if bit == "1" else FREQ_0
        tone = AMPLITUDE * max_amplitude * np.sin(2 * np.pi * freq * t)
        watermark_signal[i * bit_samples:(i + 1) * bit_samples] = tone

    if len(watermark_signal) > len(audio):
        raise ValueError("El audio es demasiado corto para incrustar el watermark.")

    audio[: len(watermark_signal)] += watermark_signal

    # Evitar clipping al volver al rango del tipo original.
    if np.issubdtype(original_dtype, np.integer):
        info = np.iinfo(original_dtype)
        audio = np.clip(audio, info.min, info.max)

    wavfile.write(output_path, sample_rate, audio.astype(original_dtype))


def extract_watermark(input_path: str) -> int | None:
    """Intenta extraer un código incrustado con embed_watermark. Devuelve None si no encuentra nada fiable."""
    sample_rate, audio = wavfile.read(input_path)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float64)

    bit_samples = int(BIT_DURATION * sample_rate)
    total_samples_needed = bit_samples * CODE_BITS

    if len(audio) < total_samples_needed:
        return None

    bits = ""
    for i in range(CODE_BITS):
        segment = audio[i * bit_samples:(i + 1) * bit_samples]
        magnitude = np.abs(np.fft.rfft(segment))
        freqs = np.fft.rfftfreq(len(segment), d=1 / sample_rate)

        mag_0 = magnitude[np.argmin(np.abs(freqs - FREQ_0))]
        mag_1 = magnitude[np.argmin(np.abs(freqs - FREQ_1))]

        bits += "1" if mag_1 > mag_0 else "0"

    return _bits_to_int(bits)


def _cli() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "embed" and len(sys.argv) == 5:
        _, _, input_path, code_str, output_path = sys.argv
        embed_watermark(input_path, int(code_str), output_path)
        print(f"Watermark {code_str} incrustado -> {output_path}")

    elif command == "extract" and len(sys.argv) == 3:
        _, _, input_path = sys.argv
        code = extract_watermark(input_path)
        print(f"Código extraído: {code}" if code is not None else "No se detectó ningún watermark.")

    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()

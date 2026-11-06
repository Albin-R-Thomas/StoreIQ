"""Bounded offline decoding. Uploaded audio is never used as a URL or shell command."""

import array
import io
import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from fastapi import HTTPException

MAX_BYTES = 10 * 1024 * 1024
MAX_SECONDS = 120
FORMATS = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/ogg": "ogg",
    "application/ogg": "ogg",
    "audio/webm": "matroska",
    "video/webm": "matroska",
    "audio/mp4": "mov",
    "audio/x-m4a": "mov",
    "video/mp4": "mov",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
}


def normalize(content: bytes, media_type: str) -> tuple[bytes, float]:
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Upload a nonempty audio file no larger than 10 MiB")
    if media_type not in FORMATS:
        raise HTTPException(415, "Use WAV, MP3, OGG, WebM, M4A/MP4 or FLAC audio")
    binary = shutil.which(os.getenv("FFMPEG_PATH", "ffmpeg"))
    if not binary and not os.getenv("FFMPEG_PATH"):
        # The wheel bundles a decoder on supported desktop platforms. No download
        # or external service is needed at runtime; explicit overrides still fail.
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            binary = get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            binary = None
    if not binary:
        raise HTTPException(503, "Audio decoding unavailable. Install FFmpeg or use typed input.")
    with tempfile.TemporaryDirectory(prefix="storeiq-audio-") as directory:
        source = Path(directory) / "input.audio"
        source.write_bytes(content)
        try:
            result = subprocess.run(
                [
                    binary,
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-f",
                    FORMATS[media_type],
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-t",
                    str(MAX_SECONDS + 1),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "s16le",
                    "pipe:1",
                ],
                capture_output=True,
                timeout=20,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(422, "Audio decoding timed out. Try a shorter recording.") from exc
        except OSError as exc:
            raise HTTPException(503, "Audio decoder unavailable; use typed input.") from exc
    pcm = result.stdout
    if result.returncode or not pcm or len(pcm) % 2:
        raise HTTPException(422, "Cannot decode this audio. Upload a valid recording.")
    duration = len(pcm) / 32000
    if duration > MAX_SECONDS:
        raise HTTPException(422, "Voice notes must be at most two minutes long")
    samples = array.array("h", pcm)
    if math.sqrt(sum(x * x for x in samples) / len(samples)) < 20:
        raise HTTPException(422, "Audio is empty or too quiet. Record again or type the details.")
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(pcm)
    return output.getvalue(), duration

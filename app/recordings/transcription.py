from typing import Protocol

from app.core.errors import IntegrationNotConfigured


class Transcriber(Protocol):
    async def transcribe(self, media_id: str) -> str: ...


class PendingTranscriber:
    async def transcribe(self, media_id: str) -> str:
        raise IntegrationNotConfigured(
            "Audio download and transcription are not wired yet. Use mock_recording_text."
        )


def mock_transcribe(mock_recording_text: str) -> str:
    """Explicit test seam: text replaces audio download and speech-to-text."""
    return mock_recording_text

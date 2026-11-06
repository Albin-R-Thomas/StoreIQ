from typing import Literal, Protocol

from pydantic import ConfigDict, Field, StrictBool

from app.messaging.contracts import Contract
from app.web.actions import Home

Language = Literal["en", "hi", "mr"]


class Transcript(Contract):
    text: str = Field(min_length=1, max_length=4000)
    languages: list[str] = Field(default_factory=list, max_length=10)


class Translation(Contract):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=4000)


class SpeechResult(Contract):
    transcript: Transcript
    translation: Translation | None = None


class CombinedSpeechProvider(Protocol):
    name: str
    combined_translation: bool

    async def transcribe_and_translate(
        self, wav: bytes, language: Language | None, target: Language | None
    ) -> SpeechResult: ...


class Prepare(Contract):
    revision: int = Field(ge=1)
    customer_version: int = Field(ge=1)
    transcript: str = Field(min_length=1, max_length=4000)
    purpose: Literal["home", "note"]
    target_language: Language | None = None


class Confirm(Contract):
    revision: int = Field(ge=1)
    customer_version: int = Field(ge=1)
    confirmed: StrictBool
    home: Home | None = None


class Revision(Contract):
    revision: int = Field(ge=1)


class SpeechProvider(Protocol):
    name: str

    async def transcribe(self, wav: bytes, language: Language | None) -> Transcript: ...


class TranslationProvider(Protocol):
    name: str

    async def translate(self, text: str, target: Language) -> Translation: ...

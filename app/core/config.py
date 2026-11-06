from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://store_iq:store_iq_dev@localhost:5432/store_iq"
    enable_dev_routes: bool = True
    ai_provider: Literal["mock", "openai"] = "mock"
    ai_timeout_seconds: float = Field(default=15, gt=0, le=120)
    openai_api_key: SecretStr = SecretStr("")
    ai_model: str = ""
    rag_provider: Literal["bm25", "disabled"] = "bm25"
    rag_corpus_path: Path = Path("fixtures/knowledge_base/documents.json")
    rag_top_k: int = Field(default=3, ge=1, le=10)
    rag_chunk_words: int = Field(default=160, ge=1, le=2000)
    rag_overlap_words: int = Field(default=30, ge=0)
    rag_k1: float = Field(default=1.2, gt=0)
    rag_b: float = Field(default=0.75, ge=0, le=1)
    meta_mode: Literal["mock", "live"] = "mock"
    # Active messaging boundary; legacy META_MODE does not control this adapter.
    whatsapp_provider: str = "mock"
    voice_provider: str = "azure"
    voice_model: str = "gpt-transcribe"
    voice_translation_provider: str = "azure"
    azure_speech_key: SecretStr = SecretStr("")
    azure_speech_region: str = ""
    azure_translator_key: SecretStr = SecretStr("")
    azure_translator_region: str = ""
    meta_access_token: SecretStr = SecretStr("")
    meta_phone_number_id: str = ""
    meta_api_version: str = ""
    meta_verify_token: SecretStr = SecretStr("")
    meta_app_secret: SecretStr = SecretStr("")
    meta_test_recipients: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_chunking(self):
        if self.rag_overlap_words >= self.rag_chunk_words:
            raise ValueError("RAG_OVERLAP_WORDS must be smaller than RAG_CHUNK_WORDS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Unserved scaffold retained only for its pre-existing adapter regression tests.

The deployed entry point is app.main:app. Do not deploy this compatibility app.
"""

from fastapi import FastAPI

from app.conversations.router import router as conversations
from app.meta.mock_router import router as mock_text
from app.recordings.router import router as recordings
from app.retrieval.router import router as retrieval


def create_app():
    app = FastAPI(title="Legacy adapter regression harness")
    for router in (conversations, mock_text, recordings, retrieval):
        app.include_router(router, prefix="/api/v1")
    return app

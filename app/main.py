"""Same-origin Store IQ website with authenticated text and reviewed voice input."""

import asyncio
import contextlib
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.messaging.router import router as messaging_router
from app.voice.router import router as voice_router
from app.web.api import reminders, router
from app.web.store import initialize, transaction


@asynccontextmanager
async def lifespan(app):
    initialize()
    from app.web import message_jobs

    message_jobs.recover()
    task = asyncio.create_task(reminders())
    yield
    task.cancel()
    await message_jobs.stop()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def create_app():
    application = FastAPI(
        title="Store IQ Web API",
        version="1.0.0",
        description="Associate workspace with text, reviewed audio uploads and synthetic data.",
        lifespan=lifespan,
    )

    @application.exception_handler(sqlite3.OperationalError)
    async def storage_failure(request: Request, exc: sqlite3.OperationalError):
        logging.getLogger(__name__).error("Database unavailable: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Store data is temporarily unavailable. Retry shortly."},
        )

    @application.middleware("http")
    async def security(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            allowed = os.getenv("PUBLIC_ORIGIN", str(request.base_url).rstrip("/"))
            if origin and urlsplit(origin).netloc != urlsplit(allowed).netloc:
                return JSONResponse(
                    status_code=403, content={"detail": "Cross-origin writes are not permitted"}
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    status_code=403, content={"detail": "Cross-site writes are not permitted"}
                )
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid content length"})
            audio_upload = (
                request.method == "POST"
                and request.url.path.startswith("/api/customers/")
                and request.url.path.endswith("/voice")
                and len(request.url.path.split("/")) == 5
            )
            if length > (10 * 1024 * 1024 if audio_upload else 100000):
                return JSONResponse(status_code=413, content={"detail": "Request too large"})
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Permissions-Policy": "microphone=(self), camera=(), geolocation=()",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            }
        )
        if request.url.path.startswith(("/api", "/share")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live", tags=["health"])
    def live():
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"])
    def ready():
        try:
            with transaction() as db:
                db.execute("SELECT 1 FROM records LIMIT 1")
            return {"status": "ready"}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "database_unavailable"})

    application.include_router(router)
    application.include_router(messaging_router)
    application.include_router(voice_router)
    dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if (dist / "assets").exists():
        application.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @application.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith(("api/", "health/")):
            return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return JSONResponse(
            status_code=503,
            content={"detail": "Build frontend: cd frontend; npm install; npm run build"},
        )

    return application


app = create_app()

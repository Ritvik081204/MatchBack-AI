from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from . import config, models as m
from .ai.llm_service import llm
from .database import SessionLocal, init_db
from .routers import matches, players

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("matchback")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        empty = not db.scalar(select(func.count()).select_from(m.Match))
    if empty and config.SAMPLES_DIR.exists():
        from .data.ingestion import ingest_files
        files = sorted(config.SAMPLES_DIR.glob("*.json"))
        log.info("Database empty - importing %d bundled sample matches", len(files))
        log.info("Import report: %s", ingest_files(files))
    log.info("LLM status: %s", llm.status(force=True))
    if llm.available:  # load the model into memory in the background so the first real request isn't a cold start
        import threading
        threading.Thread(target=lambda: llm.generate("Reply with OK.", "OK?", 2), daemon=True).start()
    yield


app = FastAPI(title="MatchBack AI API", version="1.0.0",
              description="Match catch-up, timeline, milestones, turning points and Q&A over Cricsheet ball-by-ball data.",
              lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(matches.router)
app.include_router(players.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": [
        {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()]})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong while processing this match."})


@app.get("/api/health")
def health():
    with SessionLocal() as db:
        n = db.scalar(select(func.count()).select_from(m.Match))
    return {"status": "ok", "matches": n, "llm": llm.status(), "version": app.version}

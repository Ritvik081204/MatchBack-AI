"""Vercel entry point: Vercel auto-detects the FastAPI `app` exported here and keeps the original request paths."""
from app.main import app  # noqa: F401

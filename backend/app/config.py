"""Central configuration. Everything is optional: the app runs with zero env vars."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'matchback.db').as_posix()}")
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", BACKEND_DIR / "data" / "samples"))
CACHE_DIR = Path(os.getenv("CRICSHEET_CACHE_DIR", BACKEND_DIR / "data" / "cricsheet_cache"))

# --- AI (all optional) ---
LLM_ENABLED = _bool("LLM_ENABLED", True)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "90"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# Cricsheet bulk downloads used by `python -m app.data.ingestion --download`
CRICSHEET_DOWNLOADS = {
    "ipl": "https://cricsheet.org/downloads/ipl_male_json.zip",
    "t20is_male": "https://cricsheet.org/downloads/t20s_male_json.zip",
    "t20is_female": "https://cricsheet.org/downloads/t20s_female_json.zip",
    "odis_male": "https://cricsheet.org/downloads/odis_male_json.zip",
    "odis_female": "https://cricsheet.org/downloads/odis_female_json.zip",
    "tests_male": "https://cricsheet.org/downloads/tests_male_json.zip",
    "tests_female": "https://cricsheet.org/downloads/tests_female_json.zip",
    "wpl": "https://cricsheet.org/downloads/wpl_json.zip",
}

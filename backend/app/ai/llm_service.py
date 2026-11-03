"""Optional local LLM via Ollama. Every caller must work when this returns None."""
from __future__ import annotations

import json
import logging
import re
import time

import httpx

from .. import config

log = logging.getLogger("matchback.llm")
PREFERRED = ("llama3.2", "llama3.1", "qwen2.5", "gemma", "phi3", "mistral", "llama3")
_NUM = re.compile(r"\d+(?:\.\d+)?")


class LLMService:
    def __init__(self) -> None:
        self._status: dict | None = None
        self._checked_at = 0.0
        self.model: str | None = None

    def status(self, force: bool = False) -> dict:
        """Cheap availability probe (cached 20s so a stopped Ollama does not slow every request)."""
        if not config.LLM_ENABLED:
            return {"available": False, "reason": "disabled (LLM_ENABLED=false)", "model": None, "host": config.OLLAMA_HOST}
        if not force and self._status and time.time() - self._checked_at < 20:
            return self._status
        try:
            r = httpx.get(f"{config.OLLAMA_HOST}/api/tags", timeout=1.5)
            r.raise_for_status()
            names = [m["name"] for m in r.json().get("models", [])]
            model = self._pick(names)
            self.model = model
            self._status = ({"available": True, "model": model, "host": config.OLLAMA_HOST, "installed": names}
                            if model else {"available": False, "reason": "Ollama is running but has no models installed",
                                           "model": None, "host": config.OLLAMA_HOST, "installed": []})
        except Exception as exc:  # noqa: BLE001 - any failure means "use the fallback"
            self.model = None
            self._status = {"available": False, "reason": f"Ollama not reachable ({type(exc).__name__})", "model": None,
                            "host": config.OLLAMA_HOST}
        self._checked_at = time.time()
        return self._status

    @staticmethod
    def _pick(names: list[str]) -> str | None:
        if not names:
            return None
        if config.OLLAMA_MODEL in names:
            return config.OLLAMA_MODEL
        for pref in PREFERRED:
            for n in names:
                if n.lower().startswith(pref):
                    return n
        return names[0]

    @property
    def available(self) -> bool:
        return bool(self.status()["available"])

    def generate(self, system: str, prompt: str, max_tokens: int = 400) -> str | None:
        if not self.available:
            return None
        try:
            r = httpx.post(
                f"{config.OLLAMA_HOST}/api/chat",
                json={"model": self.model, "stream": False, "keep_alive": "10m",
                      "options": {"temperature": 0.2, "num_predict": max_tokens},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
                timeout=config.OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            text = (r.json().get("message") or {}).get("content", "").strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM generation failed (%s); using rule-based fallback", exc)
            self._status = None  # re-probe next time
            return None


llm = LLMService()


def numbers_in(text: str) -> set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUM.findall(text)}


def grounding_violations(output: str, context: object) -> list[str]:
    """Numbers in the LLM output that do not appear anywhere in the facts it was given.

    A model that adds or computes a figure of its own is detected and rejected by the callers.
    Digits 0-10 are tolerated (ordinals such as 'second', 'two wickets')."""
    allowed = numbers_in(context if isinstance(context, str) else json.dumps(context, default=str))
    return sorted(n for n in numbers_in(output) if n not in allowed and not (n.isdigit() and int(n) <= 10))

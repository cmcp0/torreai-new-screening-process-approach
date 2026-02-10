import logging
from typing import Any

import httpx

from src.wiring import get_settings

logger = logging.getLogger(__name__)


async def ollama_chat(system: str = "", user: str = "") -> str:
    """Call Ollama POST /api/chat; returns message.content. Uses config ollama_base_url, ollama_chat_model, ollama_timeout."""
    settings = get_settings()
    base = (settings.ollama_base_url or "").strip().rstrip("/")
    if not base:
        return "Ollama is not configured."
    url = f"{base}/api/chat"
    payload = {
        "model": settings.ollama_chat_model,
        "messages": [
            {"role": "system", "content": system or ""},
            {"role": "user", "content": user or ""},
        ],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data: dict[str, Any] = r.json()
        message = data.get("message") or {}
        content = message.get("content") or ""
        return content.strip()
    except Exception as e:
        logger.warning("Ollama chat failed: %s", e)
        return "I couldn't generate a response right now."

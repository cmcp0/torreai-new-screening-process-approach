import asyncio
import shutil
import tempfile
from pathlib import Path

import httpx


def _extension_from_codec(codec: str) -> str:
    c = (codec or "").lower().strip()
    if "webm" in c:
        return ".webm"
    if "wav" in c:
        return ".wav"
    if "mp3" in c:
        return ".mp3"
    if "pcm" in c:
        return ".pcm"
    return ".bin"


async def transcribe_audio(
    chunks: list[bytes],
    codec: str,
    sample_rate_hz: int,
    stt_base_url: str = "",
    stt_api_key: str = "",
    stt_model: str = "whisper-1",
    timeout_seconds: float = 60.0,
) -> str:
    """
    Real transcription adapter chain:
    1) OpenAI-compatible /audio/transcriptions endpoint if stt_base_url is configured.
    2) Local whisper CLI if available.
    3) Best-effort UTF-8 decode fallback for development/test safety.
    """
    if not chunks:
        return ""

    payload = b"".join(chunks)
    if not payload:
        return ""

    ext = _extension_from_codec(codec)
    with tempfile.TemporaryDirectory(prefix="screening-audio-") as tmpdir:
        audio_path = Path(tmpdir) / f"input{ext}"
        audio_path.write_bytes(payload)

        if (stt_base_url or "").strip():
            out = await _transcribe_via_http(
                audio_path=audio_path,
                base_url=stt_base_url.strip(),
                api_key=(stt_api_key or "").strip(),
                model=(stt_model or "whisper-1").strip(),
                timeout_seconds=timeout_seconds,
            )
            if out:
                return out

        out = await _transcribe_via_whisper_cli(audio_path)
        if out:
            return out

    # Safe fallback: never treat known audio codecs as plain text.
    if _looks_like_binary_audio(payload, codec):
        return ""
    # Development convenience for text-like payloads only.
    decoded = payload.decode("utf-8", errors="ignore").strip()
    return decoded if _looks_like_human_text(decoded) else ""


def _looks_like_binary_audio(payload: bytes, codec: str) -> bool:
    c = (codec or "").lower().strip()
    if any(k in c for k in ("webm", "opus", "wav", "mp3", "pcm")):
        return True
    # Null bytes are a strong binary signal.
    if b"\x00" in payload:
        return True
    return False


def _looks_like_human_text(text: str) -> bool:
    if not text:
        return False
    printable = sum(1 for ch in text if ch.isprintable() and ch not in "\x00\x01\x02\x03\x04\x05\x06\x07\x08")
    ratio = printable / max(1, len(text))
    return ratio >= 0.9


async def _transcribe_via_http(
    audio_path: Path,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> str:
    url = base_url.rstrip("/") + "/audio/transcriptions"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            with audio_path.open("rb") as fh:
                files = {"file": (audio_path.name, fh, "application/octet-stream")}
                data = {"model": model}
                resp = await client.post(url, headers=headers, files=files, data=data)
        if resp.status_code >= 400:
            return ""
        body = resp.json()
        text = body.get("text") if isinstance(body, dict) else None
        return text.strip() if isinstance(text, str) else ""
    except Exception:
        return ""


async def _transcribe_via_whisper_cli(audio_path: Path) -> str:
    whisper_bin = shutil.which("whisper")
    if not whisper_bin:
        return ""

    output_dir = audio_path.parent

    def _run() -> str:
        import subprocess

        cmd = [
            whisper_bin,
            str(audio_path),
            "--model",
            "base",
            "--language",
            "en",
            "--task",
            "transcribe",
            "--output_format",
            "txt",
            "--output_dir",
            str(output_dir),
        ]
        try:
            subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            txt_path = output_dir / f"{audio_path.stem}.txt"
            if not txt_path.exists():
                return ""
            return txt_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""

    return await asyncio.to_thread(_run)

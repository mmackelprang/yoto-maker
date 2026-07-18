"""Optional AI picture generation.

**Off by default.** The whole app works without this — auto-grab, upload, and
the icon library need no key. AI only becomes available if an image API key is
configured (env var ``YOTO_MAKER_AI_KEY`` or ``OPENAI_API_KEY``, or the
``ai_api_key`` setting). When absent, :func:`ai_available` returns False and the
UI simply hides the AI tab.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

from ..config import get_config
from ..settings import get_settings

_OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"


class AIUnavailableError(RuntimeError):
    """Raised when AI generation is requested but no key is configured."""


def _api_key() -> str | None:
    return (
        get_settings().get("ai_api_key")
        or os.environ.get("YOTO_MAKER_AI_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or None
    )


def ai_available() -> bool:
    return bool(_api_key())


def generate_image(prompt: str, out_dir: str | Path, *, name: str = "ai_image") -> Path:
    """Generate a kid-friendly illustration from ``prompt``. Requires a key."""
    key = _api_key()
    if not key:
        raise AIUnavailableError(
            "AI pictures aren't turned on. You can still use a YouTube picture, "
            "upload your own, or pick one from the icon library."
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    styled = (
        f"A cute, friendly, colorful children's illustration of: {prompt}. "
        "Simple, warm, storybook style, centered, plain background."
    )
    payload = {
        "model": get_settings().get("ai_model", "gpt-image-1"),
        "prompt": styled,
        "size": "1024x1024",
        "n": 1,
    }
    try:
        resp = httpx.post(
            _OPENAI_IMAGE_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()["data"][0]
    except httpx.HTTPStatusError as exc:
        raise AIUnavailableError(
            "The AI picture service refused the request. Please check the API key."
        ) from exc
    except Exception as exc:
        raise AIUnavailableError(
            "We couldn't reach the AI picture service. Please try again later."
        ) from exc

    out = out_dir / f"{name}.png"
    if data.get("b64_json"):
        out.write_bytes(base64.b64decode(data["b64_json"]))
    elif data.get("url"):
        img = httpx.get(data["url"], timeout=90)
        img.raise_for_status()
        out.write_bytes(img.content)
    else:  # pragma: no cover - defensive
        raise AIUnavailableError("The AI service returned no image.")
    return out

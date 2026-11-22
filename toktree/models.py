"""Context-window presets for the "will it fit?" check."""

from __future__ import annotations

import re

# Windows as of 2026-11. Override any of them numerically:
#   --model 200000  or  --model 200k  or  --model 1m
MODELS = {
    "gpt-4o": 128_000,
    "gpt-4.1": 1_000_000,
    "gpt-5": 400_000,
    "claude-sonnet": 200_000,
    "claude-opus": 200_000,
    "gemini-flash": 1_000_000,
    "gemini-pro": 1_000_000,
    "deepseek": 128_000,
    "qwen-max": 131_072,
    "kimi": 256_000,
}

# Shown when --model is not given.
DEFAULT_FIT_MODELS = ["claude-sonnet", "gpt-4o", "gemini-flash"]

_NUM_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([kKmM]?)[bB]?$")
_UNITS = {"k": 1_000, "m": 1_000_000, "": 1}


def parse_model(value: str) -> tuple[str, int]:
    """Resolve --model to (label, window_tokens).

    Accepts preset names ("claude-sonnet"), sizes ("128k", "1m") and raw
    token counts ("200000"). Raises ValueError with a helpful message.
    """
    key = value.strip().lower()
    if key in MODELS:
        return key, MODELS[key]
    if key == "help":
        raise ValueError(_known_models_msg())
    m = _NUM_RE.match(key)
    if m:
        num = float(m.group(1)) * _UNITS[m.group(2)]
        window = int(num)
        if window <= 0:
            raise ValueError("window size must be positive")
        return value.strip(), window
    raise ValueError(_known_models_msg())


def _known_models_msg() -> str:
    known = ", ".join(sorted(MODELS))
    return (
        f"unknown --model value; use a preset name ({known}), "
        f"a size like 128k / 1m, or a raw token count like 200000"
    )

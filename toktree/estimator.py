"""Token estimation: zero-dependency heuristic by default, tiktoken when available."""

from __future__ import annotations

import re
from pathlib import Path

# CJK ideographs (incl. Ext-A and compatibility) + Hangul syllables: ~1 token/char.
_CJK_RE = re.compile(
    "[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff"
    "\uac00-\ud7af]"
)
# Kana: BPE tends to pack kana more densely than ideographs.
_KANA_RE = re.compile("[\u3040-\u30ff\u31f0-\u31ff]")

# tiktoken is an optional accuracy upgrade, never a requirement.
_tiktoken_enc = None
_tiktoken_failed = False


def _get_tiktoken():
    global _tiktoken_enc, _tiktoken_failed
    if _tiktoken_enc is not None or _tiktoken_failed:
        return _tiktoken_enc
    try:
        import tiktoken  # type: ignore

        _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Missing package, offline machine (BPE download fails), anything else.
        _tiktoken_failed = True
        _tiktoken_enc = None
    return _tiktoken_enc


def heuristic_tokens(text: str) -> int:
    """Estimate tokens from character classes.

    ASCII (code, prose): ~4 chars/token. CJK ideographs & Hangul: ~1 token/char.
    Kana and everything else: ~0.75 tokens/char. Typical error is within ±20%.
    """
    if not text:
        return 0
    ascii_n = len(text.encode("ascii", "ignore"))
    tokens = ascii_n / 4.0
    nonascii_n = len(text) - ascii_n
    if nonascii_n:
        cjk_n = len(_CJK_RE.findall(text))
        kana_n = len(_KANA_RE.findall(text))
        other_n = nonascii_n - cjk_n - kana_n
        tokens += cjk_n * 1.0 + kana_n * 0.75 + other_n * 0.75
    return max(1, round(tokens))


def tiktoken_tokens(text: str) -> int:
    """Exact cl100k_base count. Raises if tiktoken is unavailable."""
    enc = _get_tiktoken()
    if enc is None:
        raise RuntimeError("tiktoken is not available")
    return len(enc.encode(text, disallowed_special=()))


def estimator_available(name: str) -> bool:
    if name == "heuristic":
        return True
    if name == "tiktoken":
        return _get_tiktoken() is not None
    raise ValueError(f"unknown estimator: {name}")


def estimate_text(text: str, estimator: str = "heuristic") -> int:
    if estimator == "tiktoken":
        return tiktoken_tokens(text)
    return heuristic_tokens(text)


def estimate_file(path: Path, estimator: str = "heuristic"):
    """Token count for one file, or None if it looks binary/unreadable."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "replace")
    return estimate_text(text, estimator)

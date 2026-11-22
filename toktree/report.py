"""Scanning, aggregation and the three report renderers (table/json/markdown)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .estimator import estimate_file
from .walker import discover_files


@dataclass
class FileEntry:
    path: str  # relative, posix-style
    tokens: int
    size: int  # bytes


@dataclass
class ScanResult:
    root: str
    estimator: str
    files: list[FileEntry] = field(default_factory=list)
    total_tokens: int = 0
    total_size: int = 0

    def by_type(self) -> list[tuple[str, int, int]]:
        """(extension, tokens, file_count) sorted by tokens desc."""
        agg: dict[str, list[int]] = {}
        for f in self.files:
            ext = Path(f.path).suffix.lower() or "(no ext)"
            a = agg.setdefault(ext, [0, 0])
            a[0] += f.tokens
            a[1] += 1
        return sorted(((ext, t, c) for ext, (t, c) in agg.items()),
                      key=lambda x: -x[1])

    def by_dir(self) -> list[tuple[str, int]]:
        """Top-level directory breakdown, sorted by tokens desc."""
        agg: dict[str, int] = {}
        for f in self.files:
            top = f.path.split("/", 1)[0] if "/" in f.path else "(root)"
            agg[top] = agg.get(top, 0) + f.tokens
        return sorted(agg.items(), key=lambda kv: -kv[1])


def scan(root: Path, estimator: str, excludes: list[str],
         no_ignore: bool) -> ScanResult:
    res = ScanResult(root=str(root), estimator=estimator)
    for path in discover_files(root, excludes, no_ignore):
        tokens = estimate_file(path, estimator)
        if tokens is None:
            continue  # sniffed as binary
        rel = path.relative_to(root).as_posix() if path != root else path.name
        size = path.stat().st_size
        res.files.append(FileEntry(rel, tokens, size))
        res.total_tokens += tokens
        res.total_size += size
    res.files.sort(key=lambda f: -f.tokens)
    return res


# ---------------------------------------------------------------- formatting

def _ansi_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


class Ansi:
    def __init__(self, enabled: bool = None):
        self.on = _ansi_enabled() if enabled is None else enabled

    def _wrap(self, code: int, s: str) -> str:
        return f"\x1b[{code}m{s}\x1b[0m" if self.on else s

    def bold(self, s): return self._wrap(1, s)
    def dim(self, s): return self._wrap(2, s)
    def red(self, s): return self._wrap(31, s)
    def green(self, s): return self._wrap(32, s)
    def cyan(self, s): return self._wrap(36, s)


def fmt_tokens(n: int) -> str:
    if n < 10_000:
        return f"{n:,}"
    if n < 1_000_000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.2f}M"


def fmt_window(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.0f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} TB"


def bar(frac: float, width: int = 16) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


def _pct(part: int, total: int) -> str:
    return f"{(100 * part / total):.1f}%" if total else "0.0%"


# ---------------------------------------------------------------- renderers

def render_table(res: ScanResult, opts, models) -> str:
    a = Ansi()
    out = []
    label = "tiktoken cl100k" if res.estimator == "tiktoken" else "heuristic (est.)"
    out.append(a.bold(f"toktree v{__version__}") + a.dim(f"  ·  {label}  ·  {res.root}"))
    out.append("")
    out.append(a.cyan("Summary"))
    mb = f" · {fmt_size(res.total_size)} text"
    out.append(f"  {len(res.files)} files · {a.bold(fmt_tokens(res.total_tokens))} tokens{mb}")
    if not res.files:
        out.append(a.dim("  (no text files found)"))
        return "\n".join(out)

    if opts.price:
        cost = res.total_tokens / 1_000_000 * opts.price
        out.append(f"  ≈ ${cost:,.2f} input cost at ${opts.price:g}/Mtok")

    # -- will it fit?
    out.append("")
    out.append(a.cyan("Will it fit?"))
    for name, window in models:
        ratio = res.total_tokens / window
        fill = bar(min(ratio, 1.0))
        if ratio <= 1.0:
            verdict = a.green(f"fits ({_pct(res.total_tokens, window)})")
        else:
            verdict = a.red(f"OVERFLOW ×{ratio:.1f}")
        out.append(f"  {name:<16} {fmt_window(window):>4}  {fill}  {verdict}")

    # -- largest files
    out.append("")
    out.append(a.cyan(f"Largest files (top {opts.top})"))
    for f in res.files[: opts.top]:
        out.append(
            f"  {fmt_tokens(f.tokens):>8}  {_pct(f.tokens, res.total_tokens):>6}"
            f"  {f.path}"
        )

    # -- by directory
    out.append("")
    out.append(a.cyan("By directory (top level)"))
    dirs = res.by_dir()
    width = max((len(d) for d, _ in dirs), default=1)
    for d, tokens in dirs[: opts.top]:
        out.append(
            f"  {d:<{width}}  {_pct(tokens, res.total_tokens):>6}  "
            f"{bar(tokens / max(res.total_tokens, 1))}  {fmt_tokens(tokens)}"
        )

    # -- by type
    out.append("")
    out.append(a.cyan("By type"))
    for ext, tokens, count in res.by_type()[: opts.top]:
        out.append(
            f"  {ext:<10} {_pct(tokens, res.total_tokens):>6}  "
            f"{fmt_tokens(tokens):>8}  ({count} files)"
        )
    return "\n".join(out)


def render_json(res: ScanResult, opts, models) -> str:
    fit = {}
    for name, window in models:
        fit[name] = {
            "window_tokens": window,
            "fits": res.total_tokens <= window,
            "used": round(res.total_tokens / window, 4) if window else 0,
        }
    doc = {
        "tool": "toktree",
        "version": __version__,
        "root": res.root,
        "estimator": res.estimator,
        "files": len(res.files),
        "total_tokens": res.total_tokens,
        "total_bytes": res.total_size,
        "fit": fit,
        "by_type": {ext: {"tokens": t, "files": c}
                    for ext, t, c in res.by_type()},
        "by_dir": {d: t for d, t in res.by_dir()},
        "largest_files": [
            {"path": f.path, "tokens": f.tokens, "bytes": f.size}
            for f in res.files[: opts.top]
        ],
        "all_files": [
            {"path": f.path, "tokens": f.tokens, "bytes": f.size}
            for f in res.files
        ],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_markdown(res: ScanResult, opts, models) -> str:
    est = "tiktoken" if res.estimator == "tiktoken" else "estimated"
    lines = [
        f"## toktree — `{res.root}`",
        "",
        f"**{len(res.files)} files · {fmt_tokens(res.total_tokens)} tokens ({est})"
        f" · {fmt_size(res.total_size)}**",
        "",
        "| model | window | used | verdict |",
        "|---|---:|---:|---|",
    ]
    for name, window in models:
        used = _pct(res.total_tokens, window)
        verdict = "✅ fits" if res.total_tokens <= window else \
            f"❌ overflow ×{res.total_tokens / window:.1f}"
        lines.append(f"| {name} | {fmt_window(window)} | {used} | {verdict} |")
    lines += ["", "**Largest files**", "", "| tokens | share | file |",
              "|---:|---:|---|"]
    for f in res.files[: opts.top]:
        lines.append(
            f"| {fmt_tokens(f.tokens)} | {_pct(f.tokens, res.total_tokens)} |"
            f" `{f.path}` |"
        )
    lines += ["", "**By type**", "", "| ext | tokens | share | files |",
              "|---|---:|---:|---:|"]
    for ext, tokens, count in res.by_type()[: opts.top]:
        lines.append(
            f"| `{ext}` | {fmt_tokens(tokens)} |"
            f" {_pct(tokens, res.total_tokens)} | {count} |"
        )
    return "\n".join(lines)

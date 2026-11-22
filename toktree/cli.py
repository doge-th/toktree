"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .estimator import estimator_available
from .models import DEFAULT_FIT_MODELS, parse_model
from .report import render_json, render_markdown, render_table, scan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="toktree",
        description="du for your LLM context window: how many tokens does "
                    "this folder cost, and does it fit in a model's context?",
        epilog="examples:  toktree .  ·  toktree src --model claude-sonnet "
               "--price 3  ·  toktree . --json",
    )
    p.add_argument("paths", nargs="*", default=["."],
                   help="files or directories to analyze (default: .)")
    p.add_argument("--top", type=int, default=10, metavar="N",
                   help="show N entries per section (default 10)")
    p.add_argument("--model", action="append", metavar="NAME",
                   help="context window to check against: preset name (claude-sonnet, "
                        "gpt-4o, gemini-flash, ...), size (128k, 1m) or raw count "
                        "(200000); repeatable")
    p.add_argument("--price", type=float, metavar="USD_PER_MTOK",
                   help="input price per 1M tokens to estimate cost")
    p.add_argument("--estimator", choices=["auto", "heuristic", "tiktoken"],
                   default="auto",
                   help="tiktoken gives exact cl100k counts but needs the optional "
                        "package (default: auto = heuristic, zero dependencies)")
    p.add_argument("--exclude", action="append", metavar="GLOB",
                   help="extra path glob to skip (repeatable)")
    p.add_argument("--no-ignore", action="store_true",
                   help="walk everything, including .gitignore'd files")
    p.add_argument("--json", dest="fmt", action="store_const", const="json",
                   help="machine-readable JSON output")
    p.add_argument("--markdown", "--md", dest="fmt", action="store_const",
                   const="markdown", help="markdown output for issues/PRs")
    p.add_argument("--version", action="version", version=f"toktree {__version__}")
    return p


def _resolve_estimator(choice: str) -> str:
    if choice == "auto":
        return "heuristic"  # predictable, offline-safe default
    if not estimator_available(choice):
        print(f"toktree: --estimator tiktoken requires the optional package: "
              f"pip install tiktoken", file=sys.stderr)
        sys.exit(1)
    return choice


def main(argv=None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    if opts.top < 0:
        parser.error("--top must be >= 0")

    estimator = _resolve_estimator(opts.estimator)
    try:
        models = [parse_model(m) for m in (opts.model or DEFAULT_FIT_MODELS)]
    except ValueError as e:
        print(f"toktree: {e}", file=sys.stderr)
        return 1
    renderer = {"table": render_table, "json": render_json,
                "markdown": render_markdown}[opts.fmt or "table"]

    failed = False
    for raw in opts.paths:
        root = Path(raw)
        if not root.exists():
            print(f"toktree: no such file or directory: {raw}", file=sys.stderr)
            failed = True
            continue
        res = scan(root if root.is_dir() else root.parent, estimator,
                   opts.exclude or [], opts.no_ignore)
        if root.is_file():
            res.files = [f for f in res.files if f.path == root.name]
            res.total_tokens = sum(f.tokens for f in res.files)
            res.total_size = sum(f.size for f in res.files)
        print(renderer(res, opts, models))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

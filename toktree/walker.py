"""File discovery: git-aware inside repos, sensible defaults everywhere else."""

from __future__ import annotations

import fnmatch
import os
import subprocess
from pathlib import Path

# Directories that are noise for context-window budgeting.
DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    ".cache",
    ".idea",
    ".vscode",
    "vendor",
    "site-packages",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".icns", ".tiff",
    ".svg",
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".mp4", ".mov", ".avi",
    ".mkv", ".webm",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".db", ".sqlite", ".sqlite3", ".parquet", ".pickle", ".pkl",
    ".pyc", ".pyo", ".wasm", ".onnx", ".pt", ".pth", ".safetensors", ".gguf",
    ".lock",
}


def is_binary_path(path: Path) -> bool:
    return path.suffix.lower() in BINARY_EXTENSIONS


def _git_files(root: Path) -> list[Path] | None:
    """Tracked + untracked-but-not-ignored files, exactly as git sees them."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z",
             "--cached", "--others", "--exclude-standard"],
            capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    names = out.stdout.decode("utf-8", "replace").split("\0")
    files = []
    for name in names:
        if not name:
            continue
        p = root / name
        if p.is_file():
            files.append(p)
    return files


def _walk_files(root: Path, extra_excludes: list[str]) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in DEFAULT_EXCLUDES and not d.endswith(".egg-info")
        )
        for fname in sorted(filenames):
            rel = (rel_dir / fname).as_posix() if rel_dir.as_posix() != "." else fname
            if any(fnmatch.fnmatch(rel, pat) for pat in extra_excludes):
                continue
            files.append(root / rel)
    return files


def discover_files(root: Path, extra_excludes: list[str] | None = None,
                   no_ignore: bool = False) -> list[Path]:
    """Files to count under *root*, sorted for stable output.

    Inside a git work tree, gitignore rules are honored via `git ls-files`
    (use no_ignore=True to walk everything instead). Outside git, a default
    exclusion list keeps vendored/build noise out.
    """
    extra_excludes = extra_excludes or []
    if root.is_file():
        return [root]
    if not no_ignore:
        files = _git_files(root)
        if files is not None:
            files = [f for f in files if not is_binary_path(f)]
            if extra_excludes:
                files = [
                    f for f in files
                    if not any(fnmatch.fnmatch(f.relative_to(root).as_posix(), pat)
                               for pat in extra_excludes)
                ]
            return sorted(files)
    files = _walk_files(root, extra_excludes)
    return sorted(f for f in files if not is_binary_path(f))

# toktree 🌳

[![CI](https://img.shields.io/github/actions/workflow/status/doge-th/toktree/ci.yml?branch=main&label=CI)](https://github.com/doge-th/toktree/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

**`du` for your LLM context window.**

Point it at any folder and see how many tokens it would eat, which files are the
expensive ones, and whether it fits inside a 128k / 200k / 1M context window —
*before* your agent burns the budget. Zero dependencies, one command.

```
$ toktree .

toktree v0.1.0  ·  heuristic (est.)  ·  .

Summary
  17 files · 8,126 tokens · 31.7 KB text

Will it fit?
  claude-sonnet    200k  █░░░░░░░░░░░░░░░  fits (4.1%)
  gpt-4o           128k  █░░░░░░░░░░░░░░░  fits (6.3%)
  gemini-flash       1M  ░░░░░░░░░░░░░░░░  fits (0.8%)

Largest files (top 5)
     2,030   25.0%  toktree/report.py
       965   11.9%  toktree/cli.py
       912   11.2%  toktree/walker.py
       700    8.6%  tests/test_cli.py
       695    8.6%  toktree/estimator.py

By directory (top level)
  toktree   62.0%  ██████████░░░░░░  5,035
  tests     29.3%  █████░░░░░░░░░░░  2,378
  (root)     7.1%  █░░░░░░░░░░░░░░░  573
  .github    1.7%  ░░░░░░░░░░░░░░░░  140

By type
  .py         91.2%     7,413  (13 files)
  .toml        3.6%       289  (1 files)
  (no ext)     3.5%       284  (2 files)
  .yml         1.7%       140  (1 files)
```

*(that's toktree analyzing its own repository — the output is real)*

## Why

Every agent workflow starts with the same guess: *how much of this repo can I
paste into the prompt?* Too much and you get truncation or a billing surprise;
too conservative and the agent works half-blind. toktree turns that guess into
a number — per file, per directory, per file type — and tells you whether the
whole thing fits the model you're targeting.

## Install

```bash
pip install git+https://github.com/doge-th/toktree.git
# or, without touching your environment:
pipx install git+https://github.com/doge-th/toktree.git
uvx --from git+https://github.com/doge-th/toktree.git toktree .
```

## Usage

```bash
toktree .                          # analyze current directory
toktree src docs                   # analyze specific paths (one report each)
toktree . --model claude-sonnet    # fit check against one model
toktree . --model 128k             # ...or a raw window size: 128k, 1m, 200000
toktree . --price 3                # estimate input cost at $3 / Mtok
toktree . --json                   # machine-readable (all files included)
toktree . --markdown               # paste-ready table for issues & PRs
toktree . --top 20                 # more entries per section
toktree . --exclude "docs/**"      # skip a glob (repeatable)
toktree . --no-ignore              # include .gitignore'd files too
toktree . --estimator tiktoken     # exact cl100k_base counts (needs: pip install tiktoken)
```

Known model presets: `gpt-4o`, `gpt-4.1`, `gpt-5`, `claude-sonnet`,
`claude-opus`, `gemini-flash`, `gemini-pro`, `deepseek`, `qwen-max`, `kimi` —
or pass any size (`128k`, `1m`, `200000`). Windows are as of 2026-11; use a raw
count when a preset drifts.

`--json` output contains everything (fit checks, by-type, by-dir, largest
files, and all files), so you can build your own budget logic on top:

```bash
toktree . --json | jq '.fit["claude-sonnet"].used'
```

## Accuracy

By default toktree uses a character-class heuristic — no dependencies, no
downloads, no surprises offline:

- ASCII (code, prose): ~4 chars/token
- CJK ideographs & Hangul: ~1 token/char
- kana & other scripts: ~0.75 tokens/char

Typical error is within ±20%, which is plenty for budgeting. When you need
exact numbers, install [tiktoken](https://pypi.org/project/tiktoken/) and pass
`--estimator tiktoken` for exact `cl100k_base` counts (it downloads the BPE
table on first use).

## Behavior notes

- Inside a git repository, `.gitignore` rules are honored exactly (via
  `git ls-files`). Outside git, common noise directories (`node_modules`,
  `__pycache__`, `dist`, …) are skipped.
- Binary files are skipped by extension and by a null-byte sniff; lock files
  (`*.lock`) are treated as noise — that's usually what you want for prompt
  budgeting. Override with `--no-ignore` where applicable.
- Honors [`NO_COLOR`](https://no-color.org/); plain output when piped.

## 中文说明

**toktree = 面向大模型上下文窗口的 `du`。** 一条命令算出一个目录要吃多少
token、哪些文件最贵、能不能塞进 128k / 200k / 1M 的窗口——别让 agent 烧完
预算才发现超了。

```bash
pip install git+https://github.com/doge-th/toktree.git
toktree .                 # 当前目录的 token 预算
toktree . --model 200k    # 对照指定窗口,看塞不塞得下
toktree . --json          # 机器可读输出
```

零依赖、离线可用;装上 `tiktoken` 后加 `--estimator tiktoken` 可以拿到精确
的 cl100k_base 计数。启发式估算误差一般在 ±20% 以内,做预算完全够用。

## Related tools

- [githotspot](https://github.com/doge-th/githotspot) — churn × complexity hotspots in your git history
- [todomold](https://github.com/doge-th/todomold) — your oldest TODOs, with who wrote them and how long they've rotted
- [csvpulse](https://github.com/doge-th/csvpulse) — take the pulse of a CSV file in one command
- [awakehours](https://github.com/doge-th/awakehours) — find the hours when your whole team is actually awake
- [pyverscan](https://github.com/doge-th/pyverscan) — the oldest Python your code can run on, from the AST up

## Development

```bash
python -m unittest discover -s tests   # zero-dep test suite
```

## License

[MIT](LICENSE) © 2026 doge-th

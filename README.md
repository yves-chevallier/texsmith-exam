# TeXSmith Template Exam

[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Build system](https://img.shields.io/badge/build-hatchling-4B8BBE.svg)](https://hatch.pypa.io/latest/)
[![Package manager](https://img.shields.io/badge/deps-uv-6A5ACD.svg)](https://docs.astral.sh/uv/)
[![Docs](https://img.shields.io/badge/docs-mkdocs%20material-2E8555.svg)](https://squidfunk.github.io/mkdocs-material/)

`texsmith-template-exam` is an exam-focused template for [TeXSmith](https://github.com/yves-chevallier/texsmith).  
It provides:

- An exam LaTeX template and renderer integration.
- Markdown helpers for question structures, multiple-choice answers, and fill-in blanks.
- Solution-aware rendering to generate both student and answer-key PDFs from the same source.
- Demo content and Makefiles to quickly produce sample exam/solution outputs.

The current template branding is oriented to HEIG-VD and can be adapted over time.

## What it is

This repository contains:

- A TeXSmith template entry point: `exam`.
- A custom renderer registration for exam-specific behavior.
- Markdown extensions and rendering rules for:
  - Heading-to-question/part/subpart mapping.
  - Task-list-based multiple-choice blocks.
  - Solution callouts (`!!! solution`) with lines/grid/box options.
  - Fill-in-the-blank placeholders.
- Documentation source under `docs/`.
- Working demos under `demo/exam` and `demo/quiz`.

## Prerequisites

- Python `>=3.13`
- [uv](https://docs.astral.sh/uv/) installed
- A LaTeX environment available for TeXSmith PDF builds

## Installation

From repository root:

```bash
uv sync --group dev --group docs
```

This installs runtime deps, dev/test tools, and docs tooling.

## How to use

### 1. Prepare your exam markdown

Create one or more `.md` files using the exam syntax documented in:

- `docs/index.md`
- `docs/syntax.md`

Optional front matter can define title, author, language, and `exam.*` settings (see `demo/exam/config.yml` for a complete example).

### 2. Render with the installed template entry point

If the package is installed in your environment, use:

```bash
uv run texsmith render --template exam exam.md
```

Generate solution version from the same source:

```bash
uv run texsmith render --template exam -a solution=true exam.md
```

### 3. Render with the local template path (dev workflow)

From this repository, use the local template directly:

```bash
uv run texsmith -t src/texsmith_template_exam/exam exam.md --build
```

Solution mode:

```bash
uv run texsmith -t src/texsmith_template_exam/exam exam.md --build -a solution=true
```

### 4. Run the provided demos

Build exam + solution PDFs for the full demo:

```bash
make -C demo/exam
```

Outputs:

- `demo/exam/build/exam/exam.pdf`
- `demo/exam/build/solution/solution.pdf`

Build quiz demo:

```bash
make -C demo/quiz
```

Clean demo build artifacts:

```bash
make -C demo/exam clean
make -C demo/quiz clean
```

## Build and use documentation

### Serve docs locally (live reload)

```bash
uv run mkdocs serve
```

Then open `http://127.0.0.1:8000`.

### Build static docs

```bash
uv run mkdocs build
```

Generated site output is in `site/`.

## Development checks

Run tests:

```bash
uv run pytest
```

Run lint/format checks:

```bash
uv run ruff check .
uv run ruff format .
```

## Repository layout

- `src/texsmith_template_exam/`: package source
- `src/texsmith_template_exam/exam/`: template assets and manifest
- `docs/`: MkDocs documentation
- `demo/`: runnable examples
- `tests/`: automated tests

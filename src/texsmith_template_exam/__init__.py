"""TeXSmith exam template package."""

from __future__ import annotations

from pathlib import Path

from .markdown import exam_markdown_extensions


def template() -> Path:
    """Return the on-disk path to the exam template root."""
    exam_markdown_extensions()
    return Path(__file__).resolve().parent / "exam"

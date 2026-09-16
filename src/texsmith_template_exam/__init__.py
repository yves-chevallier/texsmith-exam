"""TeXSmith exam template package."""

from __future__ import annotations

from pathlib import Path


def template() -> Path:
    """Return the on-disk path to the exam template root."""
    return Path(__file__).resolve().parent / "exam"


__all__ = ["template"]

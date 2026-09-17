"""Git version helpers for the exam template."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any
import warnings


_GIT_VERSION: str | None = None
_GIT_VERSION_READY = False


def reset_git_cache() -> None:
    global _GIT_VERSION_READY, _GIT_VERSION
    _GIT_VERSION_READY = False
    _GIT_VERSION = None


def format_exam_version(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() != "git":
        return text

    return get_git_version()


def resolve_attribute(value: Any, _spec: Any = None, _fallback: Any = None) -> str:
    """TeXSmith attribute normaliser for ``version``.

    ``template.tex`` reaches the same function through the ``exam_version``
    Jinja filter its template class registers; the Typst loader builds its own
    environment and has no such filter, so the resolution happens while the
    attribute is resolved instead.
    """
    return format_exam_version(value)


def get_git_version() -> str:
    global _GIT_VERSION_READY, _GIT_VERSION
    if _GIT_VERSION_READY:
        return _GIT_VERSION or ""
    _GIT_VERSION_READY = True
    _GIT_VERSION = ""

    repo_root = resolve_git_root()
    if repo_root is None:
        warnings.warn(
            "version=git requested but no git repository was found; cannot resolve git version.",
            stacklevel=2,
        )
        return ""

    describe = run_git(repo_root, ["describe", "--tags", "--dirty"])
    if describe:
        _GIT_VERSION = describe
        return describe

    short = run_git(repo_root, ["rev-parse", "--short=6", "HEAD"])
    if short:
        _GIT_VERSION = short
        return short

    warnings.warn("version=git requested but git metadata could not be read.", stacklevel=2)
    return ""


def resolve_git_root() -> Path | None:
    repo = run_git(Path(__file__).resolve().parent, ["rev-parse", "--show-toplevel"])
    if not repo:
        return None
    return Path(repo)


def run_git(repo_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


__all__ = [
    "format_exam_version",
    "get_git_version",
    "reset_git_cache",
    "resolve_attribute",
    "resolve_git_root",
    "run_git",
]

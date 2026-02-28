"""Custom template hooks for the exam template."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import re
import sys as _sys
from typing import Any

from texsmith.adapters.latex.renderer import LaTeXRenderer
from texsmith.adapters.markdown import render_markdown
from texsmith.core.templates.base import WrappableTemplate

from texsmith_template_exam.exam import version as exam_version
from texsmith_template_exam.markdown import exam_markdown_extensions


__init__ = _sys.modules[__name__]

_RUNTIME_BRIDGE_PATCHED = False


def _ensure_runtime_template_overrides_bridge() -> None:
    """Expose template overrides to renderer runtime before conversion starts."""
    global _RUNTIME_BRIDGE_PATCHED
    if _RUNTIME_BRIDGE_PATCHED:
        return

    try:
        from texsmith.core.conversion import core as conversion_core
    except Exception:
        return

    original = getattr(conversion_core, "_build_runtime_common", None)
    if not callable(original):
        return
    if getattr(original, "__texsmith_exam_runtime_bridge__", False):
        _RUNTIME_BRIDGE_PATCHED = True
        return

    def _wrapped_build_runtime_common(*, binding, binder_context, document, strategy, diagrams_backend, emitter, http_user_agent):  # type: ignore[no-untyped-def]
        runtime_common = original(
            binding=binding,
            binder_context=binder_context,
            document=document,
            strategy=strategy,
            diagrams_backend=diagrams_backend,
            emitter=emitter,
            http_user_agent=http_user_agent,
        )
        overrides = getattr(binder_context, "template_overrides", None)
        if isinstance(overrides, Mapping):
            runtime_common.setdefault("template_overrides", dict(overrides))
        return runtime_common

    setattr(_wrapped_build_runtime_common, "__texsmith_exam_runtime_bridge__", True)
    setattr(conversion_core, "_build_runtime_common", _wrapped_build_runtime_common)
    _RUNTIME_BRIDGE_PATCHED = True


_ensure_runtime_template_overrides_bridge()


def _markdown_to_latex(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text.strip():
        return text
    html = render_markdown(text, exam_markdown_extensions()).html
    return _get_renderer().render(html).strip()


@lru_cache(maxsize=1)
def _get_renderer() -> LaTeXRenderer:
    return LaTeXRenderer(copy_assets=False, convert_assets=False)


def _format_exam_date(value: Any, lang: str = "fr") -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if lang.lower() not in {"fr", "french", "francais", "français"}:
        return text

    has_time = bool(re.search(r"[t\\s]\\d{2}:\\d{2}", text, re.IGNORECASE))
    candidate = text
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            dt = datetime.strptime(candidate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return text

    weekdays = [
        "lundi",
        "mardi",
        "mercredi",
        "jeudi",
        "vendredi",
        "samedi",
        "dimanche",
    ]
    months = [
        "janvier",
        "fevrier",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "aout",
        "septembre",
        "octobre",
        "novembre",
        "decembre",
    ]
    weekday = weekdays[dt.weekday()]
    month = months[dt.month - 1]
    date_part = f"{weekday.capitalize()} {dt.day} {month} {dt.year}"

    if not has_time:
        return date_part

    hour = dt.hour
    minute = dt.minute
    time_part = f"{hour}h{minute:02d}"
    return f"{date_part} à {time_part}"


def _format_exam_version(value: Any) -> str:
    return exam_version.format_exam_version(value)


class Template(WrappableTemplate):
    """Exam template with extra Jinja filters."""

    def __init__(self) -> None:
        super().__init__(Path(__file__).resolve().parent)
        self.environment.filters.setdefault("markdown_to_latex", _markdown_to_latex)
        self.environment.filters.setdefault("exam_date", _format_exam_date)
        self.environment.filters.setdefault("exam_version", _format_exam_version)

    def prepare_context(  # type: ignore[override]
        self,
        latex_body: str,
        *,
        overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_paper_format(overrides)
        return super().prepare_context(latex_body, overrides=overrides)

    def _ensure_paper_format(self, overrides: Mapping[str, Any] | None) -> None:
        if not isinstance(overrides, dict):
            return
        default_paper = self.info.get_attribute_default("paper", {})
        default_format: str | None = None
        if isinstance(default_paper, Mapping):
            default_format = default_paper.get("format")
        elif isinstance(default_paper, str):
            default_format = default_paper.strip() or None
        if not default_format:
            return

        self._inject_paper_format(overrides.get("paper"), default_format)
        press = overrides.get("press")
        if isinstance(press, dict):
            self._inject_paper_format(press.get("paper"), default_format)

    @staticmethod
    def _inject_paper_format(target: Any, default_format: str) -> None:
        if not isinstance(target, dict):
            return
        has_format = bool(target.get("format"))
        has_paper_alias = bool(target.get("paper"))
        if not has_format and not has_paper_alias:
            target["format"] = default_format

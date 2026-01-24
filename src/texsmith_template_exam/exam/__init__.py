"""Custom template hooks for the exam template."""

from __future__ import annotations

from collections.abc import Mapping
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from texsmith.adapters.latex.renderer import LaTeXRenderer
from texsmith.adapters.markdown import render_markdown
from texsmith.core.templates.base import WrappableTemplate

from texsmith_template_exam.markdown import exam_markdown_extensions

_RENDERER: LaTeXRenderer | None = None


def _markdown_to_latex(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text.strip():
        return text
    html = render_markdown(text, exam_markdown_extensions()).html
    global _RENDERER
    if _RENDERER is None:
        _RENDERER = LaTeXRenderer(copy_assets=False, convert_assets=False)
    return _RENDERER.render(html).strip()


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
            dt = datetime.strptime(candidate, "%Y-%m-%d")
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


class Template(WrappableTemplate):
    """Exam template with extra Jinja filters."""

    def __init__(self) -> None:
        super().__init__(Path(__file__).resolve().parent)
        self.environment.filters.setdefault("markdown_to_latex", _markdown_to_latex)
        self.environment.filters.setdefault("exam_date", _format_exam_date)

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

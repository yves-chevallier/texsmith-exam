"""The exam template: cover-page context and the Jinja filters template.tex uses."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from texsmith.core.templates import WrappableTemplate
from texsmith.templates.common import TemplateContextHelpers

from texsmith_template_exam.exam import version as exam_version


_WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_MONTHS = (
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
)
_FRENCH = {"fr", "french", "francais", "français"}


def markdown_to_latex(value: Any) -> str:
    """A line or two of Markdown as LaTeX — the 0.8 way: tmark parses, tmark writes.

    ``format = "markdown"`` does this for a template *attribute*, but a cover
    page rule is one item of a list, so the filter renders it here through the
    same parser and writer (``manifest._render_attribute_markdown``).
    """
    if value is None:
        return ""
    text = str(value)
    if not text.strip():
        return text

    from texsmith.readers.tmark import parse_payload
    import tmark

    payload = parse_payload(text, name="<exam template attribute>")
    return str(tmark.write(payload, "latex", {}).get("text") or "").strip()


def format_exam_date(value: Any, lang: str = "fr") -> str:
    """An ISO date as the long French form the cover page prints."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if lang.lower() not in _FRENCH:
        return text

    has_time = bool(re.search(r"[t\s]\d{2}:\d{2}", text, re.IGNORECASE))
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            moment = datetime.strptime(candidate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return text

    date_part = (
        f"{_WEEKDAYS[moment.weekday()].capitalize()} {moment.day} "
        f"{_MONTHS[moment.month - 1]} {moment.year}"
    )
    if not has_time:
        return date_part
    return f"{date_part} à {moment.hour}h{moment.minute:02d}"


def format_exam_version(value: Any) -> str:
    """``version: git`` resolved through ``git describe``, anything else verbatim."""
    return exam_version.format_exam_version(value)


class Template(TemplateContextHelpers, WrappableTemplate):
    """Exam template with the extra Jinja filters ``template.tex`` uses."""

    def __init__(self) -> None:
        super().__init__(Path(__file__).resolve().parent)
        self.environment.filters.setdefault("markdown_to_latex", markdown_to_latex)
        self.environment.filters.setdefault("exam_date", format_exam_date)
        self.environment.filters.setdefault("exam_version", format_exam_version)

    def prepare_context(  # type: ignore[override]
        self,
        latex_body: str,
        *,
        overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_paper_format(overrides)
        return super().prepare_context(latex_body, overrides=overrides)

    def _ensure_paper_format(self, overrides: Mapping[str, Any] | None) -> None:
        """A ``paper`` mapping without a ``format`` keeps the template's own default."""
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
        if not target.get("format") and not target.get("paper"):
            target["format"] = default_format


__all__ = ["Template", "format_exam_date", "format_exam_version", "markdown_to_latex"]

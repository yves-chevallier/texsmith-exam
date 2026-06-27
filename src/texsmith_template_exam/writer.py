"""Exam IR→LaTeX emitters (``@writes``) on a :class:`LaTeXWriter` subclass.

Discovered via the template manifest's ``writer`` key (texsmith v0.4.1+). The
emitters branch on the ``role`` carried by the generic ``Div``/``Span`` nodes
produced in :mod:`texsmith_template_exam.reader`, turning them into ``exam.cls``
markup; anything without an exam role falls through to the bundled behaviour.

Cross-cutting flags (solution/compact mode, choice style) are read from the
writer state's ``runtime`` (already carrying ``template_overrides``) through the
existing ``exam.mode`` / ``exam.styles`` helpers, which only need an object
exposing ``runtime`` / ``config`` — satisfied by the ``WriterState``.
"""

from __future__ import annotations

import dataclasses

from texsmith.fonts.scripts import render_moving_text
from texsmith.ir import nodes as ir
from texsmith.writers.latex import LaTeXWriter, writes

from texsmith_template_exam.exam.fillin import build_fillin_latex
from texsmith_template_exam.exam.mode import in_compact_mode, in_solution_mode, points_enabled
from texsmith_template_exam.exam.styles import choice_style
from texsmith_template_exam.exam.utils import (
    choice_label,
    is_empty_title,
    normalize_answer_text,
    normalize_points,
)


_DASH_TITLES = {"-", "\N{EN DASH}", "\N{EM DASH}"}


class _PartsState:
    """Tracks which exam.cls parts environments are currently open."""

    __slots__ = ("parts", "subparts", "subsubparts")

    def __init__(self) -> None:
        self.parts = self.subparts = self.subsubparts = False


def _close_subsubparts(st: _PartsState, out: list[str]) -> None:
    if st.subsubparts:
        out.append(r"\end{subsubparts}")
        st.subsubparts = False


def _close_subparts(st: _PartsState, out: list[str]) -> None:
    _close_subsubparts(st, out)
    if st.subparts:
        out.append(r"\end{subparts}")
        st.subparts = False


def _close_parts(st: _PartsState, out: list[str]) -> None:
    _close_subparts(st, out)
    if st.parts:
        out.append(r"\end{parts}")
        st.parts = False


def _ensure_parts(st: _PartsState, out: list[str]) -> None:
    if not st.parts:
        out.append(r"\begin{parts}")
        st.parts = True


def _ensure_subparts(st: _PartsState, out: list[str]) -> None:
    _ensure_parts(st, out)
    if not st.subparts:
        out.append(r"\begin{subparts}")
        st.subparts = True


def _ensure_subsubparts(st: _PartsState, out: list[str]) -> None:
    _ensure_subparts(st, out)
    if not st.subsubparts:
        out.append(r"\begin{subsubparts}")
        st.subsubparts = True


def _heading_latex(
    *, level: int, text: str, empty_title: bool, points: str | None, ref: str | None
) -> str:
    suffix = f"\\label{{{ref}}}" if ref else ""
    opt = f"[{points}]" if points else ""
    if level == 1:
        return (
            rf"\question{opt}{suffix}"
            if empty_title
            else rf"\titledquestion{{{text}}}{opt}{suffix}"
        )
    title = "" if empty_title else f" {text}"
    if level == 2:
        return rf"\part{opt}{title}{suffix}"
    if level == 3:
        return rf"\subpart{opt}{title}{suffix}"
    return rf"\subsubpart{opt}{title}{suffix}"


def _slugify(text: str) -> str | None:
    try:
        from slugify import slugify
    except Exception:
        return None
    return slugify(text, separator="-") or None


def _attr(node: ir.Div | ir.Span, key: str) -> str | None:
    return dict(node.attrs).get(key)


def _inline_text(nodes: tuple) -> str:
    """Concatenate the raw text carried by a run of inline IR nodes."""
    parts: list[str] = []
    for node in nodes:
        text = getattr(node, "text", None)
        if isinstance(text, str):
            parts.append(text)
        elif isinstance(node, ir.Space):
            parts.append(" ")
        else:
            content = getattr(node, "content", None)
            if isinstance(content, tuple):
                parts.append(_inline_text(content))
    return "".join(parts)


class ExamLaTeXWriter(LaTeXWriter):
    """LaTeX writer adding exam.cls emitters for the exam template."""

    # -- multiple-choice / checkbox lists ----------------------------------

    @writes(ir.Div)
    def _div(self, node: ir.Div) -> str:
        role = _attr(node, "role")
        if role == "exam-choices":
            return self._exam_choices(node)
        return super()._div(node)

    # -- fill-in blanks ----------------------------------------------------

    @writes(ir.Span)
    def _span(self, node: ir.Span) -> str:
        if _attr(node, "role") == "exam-fillin":
            return self._exam_fillin(node)
        return super()._span(node)

    def _exam_fillin(self, node: ir.Span) -> str:
        raw = _inline_text(node.content)
        attrs = _attr(node, "fillin_attrs") or ""
        answer_latex = (
            render_moving_text(
                raw,
                self.state,
                legacy_accents=self.state.legacy_accents,
                escape="\\" not in raw,
            )
            or ""
        )
        return build_fillin_latex(
            answer_raw=raw,
            answer_latex=answer_latex,
            attrs=attrs,
            context=self.state,
            solution_mode=in_solution_mode(self.state),
        )

    def _exam_choices(self, node: ir.Div) -> str:
        style = choice_style(self.state)
        env = "checkboxes" if style == "checkbox" else "choices"
        lines = ["\\begin{samepage}", "\\begin{columen}[5]", f"\\begin{{{env}}}"]

        correct_labels: list[str] = []
        for index, choice in enumerate(node.content):
            if not isinstance(choice, ir.Div) or _attr(choice, "role") != "exam-choice":
                continue
            body = self._inlines(choice.content).strip()
            if _attr(choice, "checked") == "true":
                lines.append(f"\\CorrectChoice {body}")
                correct_labels.append(choice_label(index))
            else:
                lines.append(f"\\choice {body}")

        lines.append(f"\\end{{{env}}}")
        lines.append("\\end{columen}")
        if not in_compact_mode(self.state):
            if correct_labels:
                lines.append(
                    f"\\ifprintanswers\\answerline[{', '.join(correct_labels)}]"
                    "\\else\\answerline\\fi"
                )
            else:
                lines.append("\\answerline")
        lines.append("\\end{samepage}")
        return "\n".join(lines)

    # -- headings -> questions / parts -------------------------------------

    def write(self, document: ir.Document) -> str:
        return super().write(self._rewrite_exam_headings(document))

    def _rewrite_exam_headings(self, document: ir.Document) -> ir.Document:
        """Turn the flat block list's exam-heading nodes into exam.cls structure.

        A single pre-pass replays the old single-pass DOM walk: it opens/closes
        ``parts``/``subparts``/``subsubparts`` around ``\\question``/``\\part``…,
        toggles out to plain headings via the ``heading`` attribute, and closes
        any still-open environment at the document end.
        """
        runtime = self.state.runtime
        base_level = runtime.get("base_level", 0) or 0
        st = _PartsState()
        heading_mode_level: int | None = None
        pending_answerline: str | None = None
        out: list[ir.Block] = []

        for block in document.content:
            if not (isinstance(block, ir.Div) and _attr(block, "role") == "exam-heading"):
                if (
                    pending_answerline
                    and isinstance(block, (ir.Para, ir.Plain))
                    and _inline_text(block.content).strip()
                ):
                    out.append(block)
                    out.append(ir.RawBlock("latex", pending_answerline))
                    pending_answerline = None
                else:
                    out.append(block)
                continue

            attrs = dict(block.attrs)
            level = int(attrs.get("level") or "1")
            text = self._inlines(block.content)
            plain = _inline_text(block.content)
            empty_title = is_empty_title(plain)
            points = normalize_points(attrs.get("points") or None)
            if not points_enabled(self.state):
                points = None
            answer = normalize_answer_text(attrs.get("answer") or None)
            answerline: str | None = None
            if answer and not in_compact_mode(self.state):
                rendered = (
                    render_moving_text(
                        answer,
                        self.state,
                        legacy_accents=self.state.legacy_accents,
                        escape="\\" not in answer,
                        wrap_scripts=True,
                    )
                    or ""
                )
                answerline = f"\\ifprintanswers\\answerline[{rendered}]\\else\\answerline\\fi"
            defer = bool(answerline and plain.strip() in _DASH_TITLES)
            ref = attrs.get("identifier") or _slugify(plain) or ""
            heading_attr = attrs.get("heading") == "true"
            if heading_attr:
                heading_mode_level = level
            elif isinstance(heading_mode_level, int) and level <= heading_mode_level:
                heading_mode_level = None
            rendered_level = level + base_level - 1
            use_vanilla = heading_attr or (
                isinstance(heading_mode_level, int) and level > heading_mode_level
            )

            if use_vanilla or not (1 <= rendered_level <= 4):
                close_lines: list[str] = []
                _close_parts(st, close_lines)
                if use_vanilla:
                    close_lines.append(r"\ExamQuestionsEnd")
                if close_lines:
                    out.append(ir.RawBlock("latex", "\n".join(close_lines)))
                out.append(
                    ir.Header(
                        level=min(max(rendered_level, 1), 6),
                        content=block.content,
                        identifier=ref,
                    )
                )
            else:
                lines = [r"\ExamQuestionsBegin"]
                if rendered_level == 1:
                    _close_parts(st, lines)
                elif rendered_level == 2:
                    _close_subparts(st, lines)
                    _ensure_parts(st, lines)
                elif rendered_level == 3:
                    _close_subsubparts(st, lines)
                    _ensure_subparts(st, lines)
                elif rendered_level == 4:
                    _ensure_subsubparts(st, lines)
                lines.append(
                    _heading_latex(
                        level=rendered_level,
                        text=text,
                        empty_title=empty_title,
                        points=points,
                        ref=ref or None,
                    )
                )
                out.append(ir.RawBlock("latex", "\n".join(lines)))

            if answerline:
                if defer:
                    pending_answerline = answerline
                else:
                    out.append(ir.RawBlock("latex", answerline))

        closing: list[str] = []
        _close_parts(st, closing)
        if closing:
            out.append(ir.RawBlock("latex", "\n".join(closing)))
        return dataclasses.replace(document, content=tuple(out))


__all__ = ["ExamLaTeXWriter"]

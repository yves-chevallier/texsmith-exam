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

from texsmith.fonts.scripts import render_moving_text
from texsmith.ir import nodes as ir
from texsmith.writers.latex import LaTeXWriter, writes

from texsmith_template_exam.exam.fillin import build_fillin_latex
from texsmith_template_exam.exam.mode import in_compact_mode, in_solution_mode
from texsmith_template_exam.exam.styles import choice_style
from texsmith_template_exam.exam.utils import choice_label


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


__all__ = ["ExamLaTeXWriter"]

"""Render task list checkboxes for exam.cls."""

from __future__ import annotations

from bs4.element import NavigableString, Tag
from texsmith.core.context import RenderContext

from texsmith_template_exam.exam.mode import in_compact_mode
from texsmith_template_exam.exam.styles import choice_style
from texsmith_template_exam.exam.texsmith_compat import (
    mark_processed,
    prepare_rich_text_content,
)
from texsmith_template_exam.exam.utils import choice_label


def render_exam_checkboxes(element: Tag, context: RenderContext) -> None:
    """Render task lists as exam.cls checkboxes."""
    if element.name != "ul":
        return

    prepare_rich_text_content(element, context)

    items: list[tuple[bool, str]] = []
    has_checkbox = False

    for li in element.find_all("li", recursive=False):
        if li.find(["ul", "ol"]):
            return

        checkbox_input = li.find("input", attrs={"type": "checkbox"})
        if checkbox_input is not None:
            is_checked = checkbox_input.has_attr("checked")
            checkbox_input.extract()
            text = li.get_text(strip=False).strip()
            items.append((is_checked, text))
            has_checkbox = True
            continue

        text = li.get_text(strip=False).strip()
        if text.startswith("[ ]"):
            items.append((False, text[3:].strip()))
            has_checkbox = True
        elif text.startswith("[x]") or text.startswith("[X]"):
            items.append((True, text[3:].strip()))
            has_checkbox = True
        else:
            items.append((False, text))

    if not has_checkbox:
        return

    selected_style = choice_style(context)
    if selected_style == "checkbox":
        lines = ["\\begin{samepage}", "\\begin{columen}[5]", "\\begin{checkboxes}"]
    else:
        lines = ["\\begin{samepage}", "\\begin{columen}[5]", "\\begin{choices}"]
    show_answerline = not in_compact_mode(context)
    correct_labels: list[str] = []
    for index, (checked, text) in enumerate(items):
        if checked:
            lines.append(f"\\CorrectChoice {text}")
            correct_labels.append(choice_label(index))
        else:
            lines.append(f"\\choice {text}")
    if selected_style == "checkbox":
        lines.append("\\end{checkboxes}")
        lines.append("\\end{columen}")
        if show_answerline:
            if correct_labels:
                lines.append(
                    f"\\ifprintanswers\\answerline[{', '.join(correct_labels)}]\\else\\answerline\\fi"
                )
            else:
                lines.append("\\answerline")
        lines.append("\\end{samepage}")
    else:
        lines.append("\\end{choices}")
        lines.append("\\end{columen}")
        if show_answerline:
            if correct_labels:
                lines.append(
                    f"\\ifprintanswers\\answerline[{', '.join(correct_labels)}]\\else\\answerline\\fi"
                )
            else:
                lines.append("\\answerline")
        lines.append("\\end{samepage}")

    element.replace_with(mark_processed(NavigableString("\n".join(lines) + "\n")))


__all__ = ["render_exam_checkboxes"]

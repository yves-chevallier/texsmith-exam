"""Helpers to render exam headings and parts."""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from texsmith.core.context import RenderContext
from texsmith.fonts.scripts import render_moving_text

from texsmith_template_exam.exam.mode import in_compact_mode, points_enabled
from texsmith_template_exam.exam.texsmith_compat import coerce_attribute, mark_processed
from texsmith_template_exam.exam.utils import (
    extract_dash_attrs_prefix,
    is_empty_title,
    is_truthy_attribute,
    matches_empty_title_pattern,
    normalize_answer_text,
    normalize_points,
    parse_heading_attrs,
)


_EMPTY_TITLE_PATTERN = None
_ATTRS_BLOCK_PATTERN = None
_HEADING_DASH_ATTRS_PATTERN = None


def _flag(context: RenderContext, key: str) -> bool:
    return bool(context.state.counters.get(key, 0))


def _set_flag(context: RenderContext, key: str, value: bool) -> None:
    context.state.counters[key] = 1 if value else 0


def _close_subsubparts(context: RenderContext, lines: list[str]) -> None:
    if _flag(context, "exam_subsubparts_open"):
        lines.append(r"\end{subsubparts}")
        _set_flag(context, "exam_subsubparts_open", False)


def _close_subparts(context: RenderContext, lines: list[str]) -> None:
    _close_subsubparts(context, lines)
    if _flag(context, "exam_subparts_open"):
        lines.append(r"\end{subparts}")
        _set_flag(context, "exam_subparts_open", False)


def _close_parts(context: RenderContext, lines: list[str]) -> None:
    _close_subparts(context, lines)
    if _flag(context, "exam_parts_open"):
        lines.append(r"\end{parts}")
        _set_flag(context, "exam_parts_open", False)


def _ensure_parts(context: RenderContext, lines: list[str]) -> None:
    if not _flag(context, "exam_parts_open"):
        lines.append(r"\begin{parts}")
        _set_flag(context, "exam_parts_open", True)


def _ensure_subparts(context: RenderContext, lines: list[str]) -> None:
    _ensure_parts(context, lines)
    if not _flag(context, "exam_subparts_open"):
        lines.append(r"\begin{subparts}")
        _set_flag(context, "exam_subparts_open", True)


def _ensure_subsubparts(context: RenderContext, lines: list[str]) -> None:
    _ensure_subparts(context, lines)
    if not _flag(context, "exam_subsubparts_open"):
        lines.append(r"\begin{subsubparts}")
        _set_flag(context, "exam_subsubparts_open", True)


def _answerline_latex(answer_text: str, context: RenderContext) -> str:
    answer_latex = render_moving_text(
        answer_text,
        context,
        legacy_accents=getattr(context.config, "legacy_latex_accents", False),
        escape="\\" not in answer_text,
        wrap_scripts=True,
    )
    return f"\\ifprintanswers\\answerline[{answer_latex}]\\else\\answerline\\fi"


def _iter_non_empty_siblings(element: Tag):
    for sibling in element.next_siblings:
        if isinstance(sibling, NavigableString):
            if sibling.strip():
                yield sibling
            continue
        yield sibling


def _is_code_only_paragraph(element: Tag) -> bool:
    if element.name != "p":
        return False
    content_nodes = [
        node
        for node in element.contents
        if not (isinstance(node, NavigableString) and not node.strip())
    ]
    if not content_nodes:
        return False
    return all(isinstance(node, Tag) and node.name == "code" for node in content_nodes)


def _attach_answerline_after_question(
    heading_element: Tag,
    answerline: str,
) -> None:
    for sibling in _iter_non_empty_siblings(heading_element):
        if isinstance(sibling, Tag):
            if sibling.name == "p" and _is_code_only_paragraph(sibling):
                sibling.insert_after(mark_processed(NavigableString("\n" + answerline + "\n")))
                return
            if sibling.name and sibling.name.lower() in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
        else:
            sibling.insert_after(mark_processed(NavigableString("\n" + answerline + "\n")))
            return
    heading_element.insert_after(mark_processed(NavigableString("\n" + answerline + "\n")))


def _should_defer_answerline_for_heading_text(text: str) -> bool:
    normalized = text.strip()
    return normalized in {"-", "\N{EN DASH}", "\N{EM DASH}"}


def _heading_latex(
    *,
    level: int,
    text: str,
    empty_title: bool,
    points: str | None,
    ref: str | None,
) -> str:
    suffix = f"\\label{{{ref}}}" if ref else ""
    opt = f"[{points}]" if points else ""
    if level == 1:
        if empty_title:
            return rf"\question{opt}{suffix}"
        return rf"\titledquestion{{{text}}}{opt}{suffix}"
    if level == 2:
        title = "" if empty_title else f" {text}"
        return rf"\part{opt}{title}{suffix}"
    if level == 3:
        title = "" if empty_title else f" {text}"
        return rf"\subpart{opt}{title}{suffix}"
    if level == 4:
        title = "" if empty_title else f" {text}"
        return rf"\subsubpart{opt}{title}{suffix}"
    raise ValueError(f"Unhandled heading level {level}")


def render_exam_headings(element: Tag, context: RenderContext) -> None:
    """Render Markdown headings as native exam.cls questions/parts."""
    for anchor in element.find_all("a"):
        anchor.unwrap()

    drop_title = context.runtime.get("drop_title")
    if drop_title:
        context.runtime["drop_title"] = False
        latex = context.formatter.pagestyle(text="plain")
        element.replace_with(mark_processed(NavigableString(latex)))
        return

    raw_text = element.get_text(strip=False)
    heading_attrs: dict[str, str] = {}
    stripped_heading = raw_text.strip()
    attrs_block_pattern = None if _ATTRS_BLOCK_PATTERN is None else _ATTRS_BLOCK_PATTERN
    if attrs_block_pattern is not None:
        attrs_match = attrs_block_pattern.search(stripped_heading)
    else:
        attrs_match = None
    if attrs_match:
        parsed_attrs = parse_heading_attrs(attrs_match.group("attrs"))
        if parsed_attrs:
            heading_attrs = parsed_attrs
            raw_text = stripped_heading[: attrs_match.start()].rstrip()
    if not heading_attrs:
        dash_attrs = extract_dash_attrs_prefix(stripped_heading)
        if dash_attrs:
            attrs_text, tail_text = dash_attrs
            parsed_attrs = parse_heading_attrs(attrs_text)
            if parsed_attrs:
                heading_attrs = parsed_attrs
                raw_text = tail_text or "-"
    if not heading_attrs and _HEADING_DASH_ATTRS_PATTERN is not None:
        dash_attrs_match = _HEADING_DASH_ATTRS_PATTERN.match(stripped_heading)
        if dash_attrs_match:
            parsed_attrs = parse_heading_attrs(dash_attrs_match.group("attrs"))
            if parsed_attrs:
                heading_attrs = parsed_attrs
                raw_text = "-"
    text = render_moving_text(
        raw_text,
        context,
        legacy_accents=getattr(context.config, "legacy_latex_accents", False),
        escape="\\" not in raw_text,
        wrap_scripts=True,
    )
    plain_text = BeautifulSoup(raw_text, "html.parser").get_text(strip=True)
    empty_title = is_empty_title(plain_text)
    if not empty_title:
        rendered_clean = text.replace("\\", "").strip()
        if matches_empty_title_pattern(rendered_clean):
            empty_title = True
            text = ""

    level = int(element.name[1:])
    heading_attr = is_truthy_attribute(
        coerce_attribute(element.get("heading"))
        or coerce_attribute(element.get("data-heading"))
        or heading_attrs.get("heading")
    )
    heading_mode_level = context.runtime.get("heading_mode_level")
    if heading_attr:
        context.runtime["heading_mode_level"] = level
        heading_mode_level = level
    elif isinstance(heading_mode_level, int) and level <= heading_mode_level:
        context.runtime["heading_mode_level"] = None
        heading_mode_level = None
    base_level = context.runtime.get("base_level", 0)
    rendered_level = level + base_level - 1

    ref = coerce_attribute(element.get("id"))
    points = normalize_points(
        coerce_attribute(element.get("points"))
        or coerce_attribute(element.get("data-points"))
        or heading_attrs.get("points")
    )
    if not points_enabled(context):
        points = None
    answer_text = normalize_answer_text(
        coerce_attribute(element.get("answer"))
        or coerce_attribute(element.get("data-answer"))
        or heading_attrs.get("answer")
    )
    answerline = (
        _answerline_latex(answer_text, context)
        if (answer_text and not in_compact_mode(context))
        else None
    )
    defer_answerline = bool(answerline and _should_defer_answerline_for_heading_text(raw_text))
    if not ref:
        slug = None
        try:
            from slugify import slugify

            slug = slugify(plain_text, separator="-")
        except Exception:
            slug = None
        ref = slug or None

    use_vanilla_heading = heading_attr or (
        isinstance(heading_mode_level, int) and level > heading_mode_level
    )
    lines: list[str] = []
    if use_vanilla_heading:
        _close_parts(context, lines)
        lines.append(r"\ExamQuestionsEnd")
        latex = context.formatter.heading(
            text=text,
            level=rendered_level,
            ref=ref,
            numbered=context.runtime.get("numbered", True),
        )
        if lines:
            latex = "\n".join([*lines, latex])
        if answerline and not defer_answerline:
            _attach_answerline_after_question(element, answerline)
        elif answerline and defer_answerline:
            context.runtime["pending_question_answerline"] = answerline
        element.replace_with(mark_processed(NavigableString(latex)))
        context.state.add_heading(level=rendered_level, text=plain_text, ref=ref)
        return

    lines.append(r"\ExamQuestionsBegin")
    if rendered_level == 1:
        _close_parts(context, lines)
    elif rendered_level == 2:
        _close_subparts(context, lines)
        _ensure_parts(context, lines)
    elif rendered_level == 3:
        _close_subsubparts(context, lines)
        _ensure_subparts(context, lines)
    elif rendered_level == 4:
        _ensure_subsubparts(context, lines)
    else:
        latex = context.formatter.heading(
            text=text,
            level=rendered_level,
            ref=ref,
            numbered=context.runtime.get("numbered", True),
            points=points,
        )
        element.replace_with(mark_processed(NavigableString(latex)))
        context.state.add_heading(level=rendered_level, text=plain_text, ref=ref)
        return

    lines.append(
        _heading_latex(
            level=rendered_level,
            text=text,
            empty_title=empty_title,
            points=points,
            ref=ref,
        )
    )

    latex = "\n".join(lines)
    if answerline and not defer_answerline:
        _attach_answerline_after_question(element, answerline)
    elif answerline and defer_answerline:
        context.runtime["pending_question_answerline"] = answerline
    element.replace_with(mark_processed(NavigableString(latex)))
    context.state.add_heading(level=rendered_level, text=plain_text, ref=ref)


def close_open_parts(root: Tag, context: RenderContext) -> None:
    """Close any still-open exam parts environments at document end."""
    lines: list[str] = []
    _close_parts(context, lines)
    if not lines:
        return
    root.append(NavigableString("\n" + "\n".join(lines) + "\n"))


def configure_heading_patterns(
    *,
    attrs_block_pattern: object,
    heading_dash_attrs_pattern: object,
) -> None:
    global _ATTRS_BLOCK_PATTERN, _HEADING_DASH_ATTRS_PATTERN
    _ATTRS_BLOCK_PATTERN = attrs_block_pattern
    _HEADING_DASH_ATTRS_PATTERN = heading_dash_attrs_pattern


__all__ = ["close_open_parts", "configure_heading_patterns", "render_exam_headings"]

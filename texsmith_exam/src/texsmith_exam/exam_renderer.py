"""Exam-specific LaTeX heading renderer for TeXSmith."""

from __future__ import annotations

import re

from bs4.element import NavigableString, Tag
from slugify import slugify

from texsmith.adapters.handlers._helpers import coerce_attribute, mark_processed
from texsmith.adapters.handlers.blocks import _prepare_rich_text_content
from texsmith.core.context import RenderContext
from texsmith.core.rules import RenderPhase, renders
from texsmith.fonts.scripts import render_moving_text


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


def _normalize_points(points: str | None) -> str | None:
    if points is None:
        return None
    trimmed = points.strip()
    return trimmed or None


def _is_empty_title(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    if normalized in {"_", "\\_"}:
        return True
    return normalized.replace("\\", "") == "_"


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


_SOLUTION_PATTERN = re.compile(
    r"^\s*!!!\s+solution(?:\s*\\?\{(?P<attrs>[^}]*)\\?\})?\s*$", re.IGNORECASE
)
_LINES_PATTERN = re.compile(r"\blines\s*=\s*(\d+)\b")


def _solution_env(lines_value: str | None) -> tuple[str, str]:
    if lines_value:
        begin_env = (
            f"\\begin{{solutionordottedlines}}[{lines_value}\\dottedlinefillheight]\n"
        )
        end_env = "\\end{solutionordottedlines}\n"
    else:
        begin_env = "\\begin{solution}\n"
        end_env = "\\end{solution}\n"
    return begin_env, end_env


@renders(
    "ul",
    phase=RenderPhase.INLINE,
    priority=5,
    name="exam_checkboxes",
    after_children=True,
    nestable=False,
)
def render_exam_checkboxes(element: Tag, context: RenderContext) -> None:
    """Render task lists as exam.cls checkboxes."""
    if element.name != "ul":
        return

    _prepare_rich_text_content(element, context)

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

    lines = ["\\begin{checkboxes}"]
    for checked, text in items:
        if checked:
            lines.append(f"\\CorrectChoice {text}")
        else:
            lines.append(f"\\choice {text}")
    lines.append("\\end{checkboxes}")

    element.replace_with(mark_processed(NavigableString("\n".join(lines) + "\n")))


@renders(
    "p",
    phase=RenderPhase.BLOCK,
    priority=5,
    name="solution_admonition",
    nestable=False,
)
def render_solution_admonition(element: Tag, context: RenderContext) -> None:
    """Convert solution directives into exam.cls solution environments."""
    if element.get("class"):
        return

    raw_text = element.get_text(strip=True)
    match = _SOLUTION_PATTERN.match(raw_text)
    if not match:
        return

    attrs = (match.group("attrs") or "").replace("\\", "")
    lines_value = None
    if attrs:
        lines_match = _LINES_PATTERN.search(attrs)
        if lines_match:
            lines_value = lines_match.group(1)

    begin_env, end_env = _solution_env(lines_value)

    content_nodes: list[object] = []
    cursor = element.next_sibling
    while cursor is not None:
        if isinstance(cursor, Tag):
            if cursor.name and cursor.name.lower() in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
            if cursor.name == "p":
                candidate = cursor.get_text(strip=True)
                if _SOLUTION_PATTERN.match(candidate):
                    break
        content_nodes.append(cursor)
        cursor = cursor.next_sibling

    begin_node = mark_processed(NavigableString(begin_env))
    element.replace_with(begin_node)

    last_node: object | None = None
    for node in reversed(content_nodes):
        if isinstance(node, NavigableString) and not node.strip():
            continue
        last_node = node
        break

    if last_node is None:
        begin_node.insert_after(NavigableString(end_env))
    else:
        last_node.insert_after(NavigableString(end_env))


@renders(
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    phase=RenderPhase.POST,
    name="exam_headings",
    before=("render_headings",),
)
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
    text = render_moving_text(
        raw_text,
        context,
        legacy_accents=getattr(context.config, "legacy_latex_accents", False),
        escape="\\" not in raw_text,
        wrap_scripts=True,
    )
    plain_text = element.get_text(strip=True)
    empty_title = _is_empty_title(plain_text)

    level = int(element.name[1:])
    base_level = context.runtime.get("base_level", 0)
    rendered_level = level + base_level - 1

    ref = coerce_attribute(element.get("id"))
    points = _normalize_points(
        coerce_attribute(element.get("points"))
        or coerce_attribute(element.get("data-points"))
    )
    if not ref:
        slug = slugify(plain_text, separator="-")
        ref = slug or None

    lines: list[str] = []
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
    element.replace_with(mark_processed(NavigableString(latex)))
    context.state.add_heading(level=rendered_level, text=plain_text, ref=ref)


@renders(
    "[document]",
    "body",
    "html",
    phase=RenderPhase.POST,
    name="exam_close_open_parts",
    after_children=True,
)
def close_open_parts(root: Tag, context: RenderContext) -> None:
    """Close any still-open exam parts environments at document end."""
    lines: list[str] = []
    _close_parts(context, lines)
    if not lines:
        return
    root.append(NavigableString("\n" + "\n".join(lines) + "\n"))


def register(renderer: object) -> None:
    """Entry point for texsmith.renderers to register exam handlers."""
    register_fn = getattr(renderer, "register", None)
    if callable(register_fn):
        register_fn(render_exam_checkboxes)
        register_fn(render_solution_admonition)
        register_fn(render_exam_headings)
        register_fn(close_open_parts)

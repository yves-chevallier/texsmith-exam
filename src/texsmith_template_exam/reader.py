"""Exam HTML→IR lowerings (``@reads``) layered on top of the bundled registry.

Each lowering claims a tag at a high priority, returning :data:`NotHandled` when
the element is not an exam construct so the bundled core lowering runs instead.
Exam constructs are encoded as generic :class:`~texsmith.ir.nodes.Div` /
:class:`~texsmith.ir.nodes.Span` nodes carrying a ``role`` (and a few string
attrs); the matching :class:`~texsmith_template_exam.writer.ExamLaTeXWriter`
emitters turn those roles into ``exam.cls`` markup.

This module is discovered via the template manifest's ``readers`` key (texsmith
v0.4.1+), so the lowerings apply only when the exam template renders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from texsmith.ir import nodes as ir
from texsmith.readers.html._helpers import attrs_tuple, classes, coerce_attr
from texsmith.readers.html.registry import NotHandled, ReadLevel, reads

from texsmith_template_exam.exam.utils import is_truthy_attribute


if TYPE_CHECKING:
    from bs4 import Tag
    from texsmith.readers.html.context import ReadContext


# -- multiple-choice / checkbox lists --------------------------------------


def _checkbox_state(li: Tag) -> tuple[bool, bool, list]:
    """Return ``(is_task_item, checked, content_children)`` for a list item.

    ``content_children`` are the BeautifulSoup children to lower as the choice
    body, with the task marker (an ``<input type=checkbox>`` or a leading
    ``[ ]`` / ``[x]`` text token) removed.
    """
    checkbox = li.find("input", attrs={"type": "checkbox"}, recursive=True)
    if checkbox is not None:
        checked = checkbox.has_attr("checked")
        checkbox.extract()
        return True, checked, list(li.children)

    # Plain-text task marker: the first textual content starts with [ ] / [x].
    children = list(li.children)
    from bs4.element import NavigableString

    for index, child in enumerate(children):
        if isinstance(child, NavigableString):
            text = str(child)
            stripped = text.lstrip()
            if stripped.startswith(("[ ]", "[x]", "[X]")):
                checked = stripped[1] in {"x", "X"}
                remainder = stripped[3:].lstrip()
                children[index] = NavigableString(remainder)
                return True, checked, children
            if text.strip():
                # Non-marker text first: not a task item.
                return False, False, children
    return False, False, children


@reads("ul", level=ReadLevel.BLOCK, priority=100, name="exam_choices")
def read_exam_choices(tag: Tag, ctx: ReadContext) -> ir.Div | object:
    """Lower a task-list ``<ul>`` into an exam choices block.

    Returns ``NotHandled`` for ordinary lists (no task markers) and for nested
    lists, so the bundled bullet-list lowering handles them.
    """
    items = tag.find_all("li", recursive=False)
    if not items:
        return NotHandled

    choices: list[ir.Div] = []
    saw_task_item = False
    for li in items:
        if li.find(["ul", "ol"], recursive=False) is not None:
            return NotHandled  # nested lists are not exam choices
        is_task, checked, content = _checkbox_state(li)
        if is_task:
            saw_task_item = True
        choices.append(
            ir.Div(
                content=ctx.lower_inline(content),
                attrs=attrs_tuple(
                    {"role": "exam-choice", "checked": "true" if checked else "false"}
                ),
            )
        )

    if not saw_task_item:
        return NotHandled

    return ir.Div(content=tuple(choices), attrs=attrs_tuple({"role": "exam-choices"}))


# -- fill-in blanks --------------------------------------------------------


@reads("span", level=ReadLevel.INLINE, priority=100, name="exam_fillin")
def read_exam_fillin(tag: Tag, ctx: ReadContext) -> ir.Span | object:
    """Lower ``<span class="texsmith-fillin">`` into an exam fill-in inline."""
    if "texsmith-fillin" not in classes(tag.get("class")):
        return NotHandled
    fillin_attrs = coerce_attr(tag.get("data-attrs")) or ""
    if not fillin_attrs:
        # Authored spans may carry width/scale as discrete data attributes.
        width = coerce_attr(tag.get("data-width"))
        scale = coerce_attr(tag.get("data-scale"))
        if width:
            fillin_attrs = f"w={width}"
        elif scale:
            fillin_attrs = f"char-width-scale={scale}"
    return ir.Span(
        content=ctx.lower_inline(tag.children),
        attrs=attrs_tuple({"role": "exam-fillin", "fillin_attrs": fillin_attrs}),
    )


# -- headings (questions / parts) ------------------------------------------


@reads("h1", "h2", "h3", "h4", "h5", "h6", level=ReadLevel.BLOCK, priority=100, name="exam_heading")
def read_exam_heading(tag: Tag, ctx: ReadContext) -> ir.Div:
    """Capture a heading (plus its exam attributes) for the writer pre-pass.

    Lowered to a ``Div(role=exam-heading)`` carrying the heading level and the
    ``points`` / ``answer`` / ``heading`` / id attributes, because the core
    ``Header`` node intentionally drops arbitrary attributes. The writer's
    pre-pass turns these into ``exam.cls`` questions/parts (or, for plain
    headings, back into a core ``Header``).
    """
    # Drop heading anchors (``<a>`` permalinks) before lowering the title.
    for anchor in tag.find_all("a"):
        anchor.unwrap()
    level = (tag.name or "h1")[1:]
    # ``heading`` is an HTML boolean-ish attribute (present ⇒ plain heading); an
    # absent attribute must read as false, so compute the flag here rather than
    # storing "" (which ``is_truthy_attribute`` would treat as true).
    heading_present = tag.has_attr("heading") or tag.has_attr("data-heading")
    heading_value = coerce_attr(tag.get("heading")) or coerce_attr(tag.get("data-heading"))
    heading_flag = "true" if (heading_present and is_truthy_attribute(heading_value)) else "false"
    attrs = {
        "role": "exam-heading",
        "level": level,
        "points": coerce_attr(tag.get("points")) or coerce_attr(tag.get("data-points")) or "",
        "answer": coerce_attr(tag.get("answer")) or coerce_attr(tag.get("data-answer")) or "",
        "heading": heading_flag,
        "identifier": coerce_attr(tag.get("id")) or "",
    }
    return ir.Div(content=ctx.lower_inline(tag.children), attrs=attrs_tuple(attrs))


# -- solution blocks -------------------------------------------------------


@reads("div", level=ReadLevel.BLOCK, priority=110, name="exam_solution")
def read_exam_solution(tag: Tag, ctx: ReadContext) -> ir.Div | object:
    """Lower ``<div class="texsmith-solution">`` into an exam solution block.

    Produced by the ``solution_md`` Markdown extension from ``!!! solution
    {lines/grid/box}``. The leading title paragraph is dropped; the remaining
    blocks become the solution body the writer wraps in an exam.cls environment.
    """
    if "texsmith-solution" not in classes(tag.get("class")):
        return NotHandled
    body_children = [
        child
        for child in tag.children
        if not (
            getattr(child, "name", None) == "p"
            and "texsmith-solution-title"
            in classes(getattr(child, "get", lambda _k: None)("class"))
        )
    ]
    attrs = {
        "role": "exam-solution",
        "lines": coerce_attr(tag.get("lines")) or "",
        "grid": coerce_attr(tag.get("grid")) or "",
        "box": coerce_attr(tag.get("box")) or "",
    }
    return ir.Div(content=ctx.lower_blocks(body_children), attrs=attrs_tuple(attrs))


__all__ = [
    "read_exam_choices",
    "read_exam_fillin",
    "read_exam_heading",
    "read_exam_solution",
]

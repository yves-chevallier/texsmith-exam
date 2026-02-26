"""Helpers to render solution environments and callouts."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from texsmith_template_exam.exam.texsmith_compat import (
    coerce_attribute,
    gather_classes,
    mark_processed,
    payload_is_block_environment,
    render_images,
)
from texsmith.adapters.markdown import render_markdown
from texsmith.core.context import RenderContext
from texsmith.fonts.scripts import render_moving_text

from texsmith_template_exam.exam.mode import in_compact_mode, in_solution_mode
from texsmith_template_exam.exam.styles import text_style
from texsmith_template_exam.exam.utils import expand_lines_value, normalize_box_dim
from texsmith_template_exam.markdown import exam_markdown_extensions


_SOLUTION_PATTERN = re.compile(
    r"^\s*!!!\s+solution(?:\s*\\?\{(?P<attrs>[^}]*)\\?\})?\s*$", re.IGNORECASE
)
_LINES_PATTERN = re.compile(r"\blines\s*=\s*([^\s,}]+)\b")
_GRID_PATTERN = re.compile(r"\bgrid\s*=\s*([^\s,}]+)\b")
_BOX_PATTERN = re.compile(r"\bbox\s*=\s*([^\s,}]+)\b")
_ATTRS_BLOCK_PATTERN = re.compile(r"\\?\{(?P<attrs>[^}]*)\\?\}\s*$")


def _parse_box_value(value: str) -> tuple[str, str] | None:
    raw = value.strip()
    if not raw:
        return None
    if "x" in raw:
        width_raw, height_raw = raw.split("x", 1)
        width = normalize_box_dim(width_raw)
        height = normalize_box_dim(height_raw)
        if width and height:
            return (width, height)
        return None
    return (normalize_box_dim(raw), "")


def _solution_env(
    lines_value: str | None,
    grid_value: str | None,
    box_value: str | None,
    *,
    compact_mode: bool = False,
    solution_mode: bool = False,
) -> tuple[str, str]:
    def _wrap_solution_spacing(begin_env: str, end_env: str) -> tuple[str, str]:
        if solution_mode:
            begin_env = "\\par\\smallskip\n" + begin_env
            end_env = end_env + "\\par\\smallskip\n"
        return begin_env, end_env

    if compact_mode and not solution_mode:
        return _wrap_solution_spacing(
            "\\ifprintanswers\n\\begin{solution}\n",
            "\\leavevmode\n\\end{solution}\n\\fi\n",
        )
    if lines_value:
        lines_value = lines_value.strip()
    if grid_value:
        grid_value = grid_value.strip()
    if box_value:
        box_value = box_value.strip()
        parsed = _parse_box_value(box_value)
        if parsed:
            width, height = parsed
            if height:
                center_box = width == height
                box_prefix = "\\noindent\\hfill" if center_box else "\\noindent"
                box_suffix = "\\hfill" if center_box else ""
                begin_env = "\\ifprintanswers\n\\begin{solution}\n"
                end_env = (
                    "\\leavevmode\n\\end{solution}\n\\else\n"
                    "\\par\n\\penalty 0\n\\vspace{1em}%\n"
                    f"{box_prefix}\\fbox{{\\parbox[c][{height}][c]{{{width}}}{{\\rule{{0pt}}{{{height}}}}}}}{box_suffix}%\n"
                    "\\vspace{1em}%\n\\fi\n"
                )
                return _wrap_solution_spacing(begin_env, end_env)
            if width:
                begin_env = f"\\begin{{solutionorbox}}[{width}]\n"
                end_env = "\\leavevmode\n\\end{solutionorbox}\n"
                return _wrap_solution_spacing(begin_env, end_env)

    if grid_value and grid_value.isdigit():
        grid_value = f"{grid_value}\\linefillheight"
    if grid_value:
        begin_env = f"\\begin{{solutionorgrid}}[{grid_value}]\n"
        end_env = "\\leavevmode\n\\end{solutionorgrid}\n"
        return _wrap_solution_spacing(begin_env, end_env)
    if not lines_value:
        begin_env = "\\ifprintanswers\n\\begin{solution}\n"
        end_env = "\\leavevmode\n\\end{solution}\n\\fi\n"
        return _wrap_solution_spacing(begin_env, end_env)

    if lines_value.lower() == "fill":
        if text_style == "lines":
            filler = "\\fillwithlines{\\stretch{1}}"
        elif text_style == "box":
            filler = "\\makeemptybox{\\stretch{1}}"
        else:
            filler = "\\fillwithdottedlines{\\stretch{1}}"
        begin_env = "\\ifprintanswers\n\\begin{solution}\n"
        end_env = f"\\leavevmode\n\\end{{solution}}\n\\else\n{filler}\n\\fi\n"
        return _wrap_solution_spacing(begin_env, end_env)

    if text_style == "lines":
        height = expand_lines_value(lines_value, unit_macro="linefillheight")
        begin_env = f"\\begin{{solutionorlines}}[{height}]\n"
        end_env = "\\leavevmode\n\\end{solutionorlines}\n"
        return _wrap_solution_spacing(begin_env, end_env)
    if text_style == "box":
        height = expand_lines_value(lines_value, unit_macro="linefillheight")
        begin_env = f"\\begin{{solutionorbox}}[{height}]\n"
        end_env = "\\leavevmode\n\\end{solutionorbox}\n"
        return _wrap_solution_spacing(begin_env, end_env)

    height = expand_lines_value(lines_value, unit_macro="dottedlinefillheight")
    begin_env = f"\\begin{{solutionordottedlines}}[{height}]\n"
    end_env = "\\leavevmode\n\\end{solutionordottedlines}\n"
    return _wrap_solution_spacing(begin_env, end_env)


def _convert_math_scripts(container: Tag) -> None:
    for script in list(container.find_all("script")):
        type_attr = coerce_attribute(script.get("type"))
        if type_attr is None or not type_attr.startswith("math/tex"):
            continue
        payload = script.get_text(strip=False) or ""
        payload = payload.strip()
        is_display = "mode=display" in type_attr

        if not payload:
            node = NavigableString("")
        elif is_display:
            if _payload_is_block_environment(payload):
                node = NavigableString(f"\n{payload}\n")
            else:
                node = NavigableString(f"\n$$\n{payload}\n$$\n")
        else:
            node = NavigableString(f"${payload}$")

        script.replace_with(mark_processed(node))


def render_solution_math_blocks(element: Tag, _context: RenderContext) -> None:
    """Convert math script tags early inside solution blocks."""
    classes = gather_classes(element.get("class"))
    if "texsmith-solution" not in classes:
        return
    _convert_math_scripts(element)


def render_solution_math_scripts(element: Tag, _context: RenderContext) -> None:
    """Ensure math scripts inside solution blocks survive paragraph flattening."""
    type_attr = coerce_attribute(element.get("type"))
    if type_attr is None or not type_attr.startswith("math/tex"):
        return
    payload = element.get_text(strip=False) or ""
    payload = payload.strip()
    is_display = "mode=display" in type_attr

    if not payload:
        node = NavigableString("")
    elif is_display:
        if payload_is_block_environment(payload):
            node = NavigableString(f"\n{payload}\n")
        else:
            node = NavigableString(f"\n$$\n{payload}\n$$\n")
    else:
        node = NavigableString(f"${payload}$")

    parent = element.parent
    if parent is not None and getattr(parent, "name", None) == "p":
        parent.attrs["data-texsmith-latex"] = "true"

    if element.parent is None:
        return
    element.replace_with(mark_processed(node))


def render_solution_math_paragraphs(element: Tag, _context: RenderContext) -> None:
    """Preserve math script payloads inside paragraphs before they are flattened."""
    if not element.find("script"):
        return
    _convert_math_scripts(element)
    element.attrs["data-texsmith-latex"] = "true"


def render_exam_images(element: Tag, context: RenderContext) -> None:
    """Ensure images inside solution/admonition blocks render in LaTeX."""
    render_images(element, context)


def render_solution_admonition(element: Tag, context: RenderContext) -> None:
    """Convert solution directives into exam.cls solution environments."""
    if element.get("class"):
        return

    _convert_math_scripts(element)
    for para in element.find_all("p"):
        para.attrs["data-texsmith-latex"] = "true"

    raw_text = element.get_text(strip=True)
    match = _SOLUTION_PATTERN.match(raw_text)
    if not match:
        return

    attrs = (match.group("attrs") or "").replace("\\", "")
    lines_value = None
    grid_value = None
    box_value = None
    if attrs:
        lines_match = _LINES_PATTERN.search(attrs)
        if lines_match:
            lines_value = lines_match.group(1)
        grid_match = _GRID_PATTERN.search(attrs)
        if grid_match:
            grid_value = grid_match.group(1)
        box_match = _BOX_PATTERN.search(attrs)
        if box_match:
            box_value = box_match.group(1)

    begin_env, end_env = _solution_env(
        lines_value,
        grid_value,
        box_value,
        compact_mode=in_compact_mode(context),
        solution_mode=in_solution_mode(context),
    )

    content_nodes: list[object] = []
    cursor = element.next_sibling
    while cursor is not None:
        if isinstance(cursor, Tag):
            if cursor.name and cursor.name.lower() in {"h1", "h2", "h3", "h4", "h5", "h6", "hr"}:
                break
            cursor_classes = gather_classes(cursor.get("class"))
            if "latex-raw" in cursor_classes or cursor.get("data-texsmith-latex") == "true":
                break
            if cursor.name == "p":
                candidate = cursor.get_text(strip=True)
                if _SOLUTION_PATTERN.match(candidate):
                    break
        content_nodes.append(cursor)
        cursor = cursor.next_sibling

    candidate: Tag | None = None
    for node in content_nodes:
        if isinstance(node, NavigableString) and not node.strip():
            continue
        if isinstance(node, Tag):
            candidate = node
        break

    if candidate is not None:
        pre = candidate if candidate.name == "pre" else candidate.find("pre")
        if pre is not None:
            code_text = pre.get_text()
            html = render_markdown(code_text, exam_markdown_extensions()).html
            soup = BeautifulSoup(html, "html.parser")
            _convert_math_scripts(soup)
            for para in soup.find_all("p"):
                para.attrs["data-texsmith-latex"] = "true"
            replacement_nodes = list(soup.body.contents) if soup.body else list(soup.contents)
            for new_node in replacement_nodes:
                candidate.insert_before(new_node)
            candidate.decompose()
            content_nodes = [
                node
                for node in replacement_nodes
                if not (isinstance(node, NavigableString) and not node.strip())
            ]

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


def render_solution_callouts(element: Tag, context: RenderContext) -> None:
    """Convert solution callouts into exam.cls solution environments."""
    if element.parent is None:
        return
    classes = gather_classes(element.get("class"))
    title = element.attrs.pop("data-callout-title", "")
    is_solution = (
        "solution" in classes
        or "texsmith-solution" in classes
        or title.strip().lower() == "solution"
    )
    if not is_solution:
        return

    _convert_math_scripts(element)
    for para in element.find_all("p"):
        para.attrs["data-texsmith-latex"] = "true"

    element.name = "div"
    element.attrs["data-callout-skip"] = "true"
    attrs = None
    if title:
        attrs_match = _ATTRS_BLOCK_PATTERN.search(title)
        if attrs_match:
            attrs = attrs_match.group("attrs")
            title = title[: attrs_match.start()].strip()

    if attrs is None:
        attrs = ""

    attr_values: list[str] = []
    for key in ("lines", "grid", "box"):
        if key in element.attrs:
            attr_values.append(f"{key}={element.attrs[key]}")
    if attr_values:
        attrs = ",".join([attrs, *attr_values]).strip(",")

    lines_value = None
    grid_value = None
    box_value = None
    if attrs:
        lines_match = _LINES_PATTERN.search(attrs)
        if lines_match:
            lines_value = lines_match.group(1)
        grid_match = _GRID_PATTERN.search(attrs)
        if grid_match:
            grid_value = grid_match.group(1)
        box_match = _BOX_PATTERN.search(attrs)
        if box_match:
            box_value = box_match.group(1)

    for img in list(element.find_all("img")):
        render_images(img, context)

    begin_env, end_env = _solution_env(
        lines_value,
        grid_value,
        box_value,
        compact_mode=in_compact_mode(context),
        solution_mode=in_solution_mode(context),
    )
    body = element.find("div", class_="texsmith-solution")
    title_node = element.find("p", class_="admonition-title")
    if title_node is not None:
        title_node.decompose()
    title_node = element.find("p", class_="texsmith-solution-title")
    if title_node is not None:
        title_node.decompose()
    content_nodes = list(body.contents) if body is not None else list(element.contents)
    begin_node = mark_processed(NavigableString(begin_env))
    end_node = mark_processed(NavigableString(end_env))
    if content_nodes:
        content_nodes[0].insert_before(begin_node)
        content_nodes[-1].insert_after(end_node)
        if body is not None:
            body.unwrap()
        element.unwrap()
    else:
        element.replace_with(begin_node)
        begin_node.insert_after(end_node)


def promote_solution_admonitions(element: Tag, _context: RenderContext) -> None:
    """Convert solution admonitions into exam solutions before callout handling."""
    classes = gather_classes(element.get("class"))
    if "admonition" not in classes:
        return

    title_node = element.find("p", class_="admonition-title")
    title = title_node.get_text(strip=True) if title_node else ""
    is_solution = "solution" in classes or title.strip().lower().startswith("solution")
    if not is_solution:
        return

    new_classes = [cls for cls in classes if cls not in {"admonition", "solution"}]
    if "texsmith-solution" not in new_classes:
        new_classes.append("texsmith-solution")
    element["class"] = new_classes


def render_solution_div_admonitions(element: Tag, context: RenderContext) -> None:
    """Convert solution divs before generic callout handling."""
    classes = gather_classes(element.get("class"))
    if "texsmith-solution" not in classes:
        return
    render_solution_callouts(element, context)


__all__ = [
    "render_exam_images",
    "render_solution_admonition",
    "render_solution_callouts",
    "render_solution_div_admonitions",
    "render_solution_math_blocks",
    "render_solution_math_paragraphs",
    "render_solution_math_scripts",
    "promote_solution_admonitions",
]

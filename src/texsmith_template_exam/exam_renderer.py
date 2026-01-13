"""Exam-specific LaTeX heading renderer for TeXSmith."""

from __future__ import annotations

import re

from bs4.element import NavigableString, Tag
from slugify import slugify

from texsmith.adapters.handlers._helpers import coerce_attribute, mark_processed
from texsmith.adapters.handlers.admonitions import gather_classes
from texsmith.adapters.handlers.blocks import _prepare_rich_text_content
from texsmith.adapters.handlers.code import _is_ascii_art, _resolve_code_engine
from texsmith.adapters.handlers.media import render_images as _render_images
from texsmith.core.callouts import DEFAULT_CALLOUTS, merge_callouts, normalise_callouts
from texsmith.core.context import RenderContext
from texsmith.core.rules import RenderPhase, renders
from texsmith.fonts.scripts import render_moving_text


def _flag(context: RenderContext, key: str) -> bool:
    return bool(context.state.counters.get(key, 0))


def _set_flag(context: RenderContext, key: str, value: bool) -> None:
    context.state.counters[key] = 1 if value else 0


def _ensure_solution_callout(context: RenderContext) -> None:
    callouts = context.runtime.get("callouts_definitions")
    if isinstance(callouts, dict):
        merged = dict(callouts)
    else:
        merged = merge_callouts(DEFAULT_CALLOUTS)
    if "solution" not in merged:
        merged["solution"] = {
            "background_color": "F5F5F5",
            "border_color": "9E9E9E",
            "icon": "✅",
        }
    context.runtime["callouts_definitions"] = normalise_callouts(merged)


@renders(
    "[document]",
    "body",
    "html",
    phase=RenderPhase.PRE,
    priority=5,
    name="exam_callout_defaults",
)
def set_exam_callouts(root: Tag, context: RenderContext) -> None:
    """Ensure the solution callout is registered before callouts render."""
    _ensure_solution_callout(context)


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
    cleaned = normalized.replace("\\", "").replace("\u00a0", "")
    compact = "".join(ch for ch in cleaned if not ch.isspace())
    return _EMPTY_TITLE_PATTERN.fullmatch(compact) is not None


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


_EMPTY_TITLE_PATTERN = re.compile(r"^[_\-\u2010\u2011\u2012\u2013\u2014\u2212]+$")
_SOLUTION_PATTERN = re.compile(
    r"^\s*!!!\s+solution(?:\s*\\?\{(?P<attrs>[^}]*)\\?\})?\s*$", re.IGNORECASE
)
_LINES_PATTERN = re.compile(r"\blines\s*=\s*([^\s,}]+)\b")
_GRID_PATTERN = re.compile(r"\bgrid\s*=\s*([^\s,}]+)\b")
_ATTRS_BLOCK_PATTERN = re.compile(r"\{(?P<attrs>[^}]*)\}\s*$")


def _normalize_style_choice(value: object | None, *, default: str, aliases: dict[str, str]) -> str:
    if value is None:
        return default
    candidate = str(value).strip().lower()
    if not candidate:
        return default
    return aliases.get(candidate, candidate) if candidate in aliases or candidate in aliases.values() else default


def _exam_style(context: RenderContext) -> dict[str, object]:
    overrides = context.runtime.get("template_overrides")
    if not isinstance(overrides, dict):
        return {}
    style = overrides.get("style")
    return style if isinstance(style, dict) else {}


def _in_solution_mode(context: RenderContext) -> bool:
    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        value = overrides.get("solution")
        if isinstance(value, bool):
            return value
    value = context.runtime.get("solution")
    if isinstance(value, bool):
        return value
    return False


def _choice_style(context: RenderContext) -> str:
    style = _exam_style(context)
    return _normalize_style_choice(
        style.get("choices"),
        default="alpha",
        aliases={"checkboxes": "checkbox", "check": "checkbox"},
    )


def _text_style(context: RenderContext) -> str:
    style = _exam_style(context)
    return _normalize_style_choice(
        style.get("text"),
        default="dotted",
        aliases={"dots": "dotted", "dottedlines": "dotted", "line": "lines"},
    )


def _choice_label(index: int) -> str:
    """Return A, B, ..., Z, AA, AB, ... for 0-based index."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = ""
    value = index + 1
    while value:
        value, rem = divmod(value - 1, 26)
        label = alphabet[rem] + label
    return label


def _expand_lines_value(value: str, *, unit_macro: str) -> str:
    trimmed = value.strip()
    if trimmed.isdigit():
        return f"{trimmed}\\{unit_macro}"
    return trimmed


def _solution_env(
    lines_value: str | None, grid_value: str | None, text_style: str
) -> tuple[str, str]:
    if lines_value:
        lines_value = lines_value.strip()
    if grid_value:
        grid_value = grid_value.strip()
    if grid_value and grid_value.isdigit():
        grid_value = f"{grid_value}\\linefillheight"
    if grid_value:
        begin_env = f"\\begin{{solutionorgrid}}[{grid_value}]\n"
        end_env = "\\leavevmode\n\\end{solutionorgrid}\n"
        return begin_env, end_env
    if not lines_value:
        return (
            "\\ifprintanswers\n\\begin{solution}\n",
            "\\leavevmode\n\\end{solution}\n\\fi\n",
        )

    if lines_value.lower() == "fill":
        if text_style == "lines":
            filler = "\\fillwithlines{\\stretch{1}}"
        elif text_style == "box":
            filler = "\\makeemptybox{\\stretch{1}}"
        else:
            filler = "\\fillwithdottedlines{\\stretch{1}}"
        return (
            "\\ifprintanswers\n\\begin{solution}\n",
            f"\\leavevmode\n\\end{{solution}}\n\\else\n{filler}\n\\fi\n",
        )

    if text_style == "lines":
        height = _expand_lines_value(lines_value, unit_macro="linefillheight")
        return (
            f"\\begin{{solutionorlines}}[{height}]\n",
            "\\leavevmode\n\\end{solutionorlines}\n",
        )
    if text_style == "box":
        height = _expand_lines_value(lines_value, unit_macro="linefillheight")
        return (
            f"\\begin{{solutionorbox}}[{height}]\n",
            "\\leavevmode\n\\end{solutionorbox}\n",
        )

    height = _expand_lines_value(lines_value, unit_macro="dottedlinefillheight")
    return (
        f"\\begin{{solutionordottedlines}}[{height}]\n",
        "\\leavevmode\n\\end{solutionordottedlines}\n",
    )


def _split_fenced_segments(code_text: str) -> list[tuple[str, str | None, str]]:
    """Return a list of ('text'|'code', lang, payload) segments."""
    segments: list[tuple[str, str | None, str]] = []
    buf_text: list[str] = []
    buf_code: list[str] = []
    in_fence = False
    fence_lang: str | None = None

    for raw in code_text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            fence_info = stripped[3:].strip()
            if not in_fence:
                if buf_text:
                    segments.append(("text", None, "\n".join(buf_text)))
                    buf_text = []
                in_fence = True
                fence_lang = fence_info or None
                buf_code = []
            else:
                segments.append(("code", fence_lang, "\n".join(buf_code)))
                in_fence = False
                fence_lang = None
                buf_code = []
            continue

        if in_fence:
            buf_code.append(raw)
        else:
            buf_text.append(raw)

    if in_fence:
        buf_text.append("```" + (fence_lang or ""))
        buf_text.extend(buf_code)

    if buf_text:
        segments.append(("text", None, "\n".join(buf_text)))
    return segments


def _split_fenced_block(code_text: str) -> list[tuple[str, str | None, str]]:
    if "```" not in code_text:
        return []

    segments = _split_fenced_segments(code_text)
    if not any(kind == "code" for kind, _, _ in segments):
        return []
    return segments


def _render_fenced_segments(
    segments: list[tuple[str, str | None, str]],
    context: RenderContext,
) -> str:
    parts: list[str] = []
    legacy_accents = getattr(context.config, "legacy_latex_accents", False)
    engine = _resolve_code_engine(context)

    for kind, lang, payload in segments:
        if kind == "text":
            if not payload.strip():
                continue
            text = render_moving_text(
                payload.strip(),
                context,
                legacy_accents=legacy_accents,
                escape="\\" not in payload,
                wrap_scripts=True,
            )
            parts.append(text)
            continue

        if not payload.strip():
            continue
        language = (lang or "text").strip() or "text"
        code_text = payload if payload.endswith("\n") else payload + "\n"
        baselinestretch = 0.5 if _is_ascii_art(code_text) else None
        context.state.requires_shell_escape = (
            context.state.requires_shell_escape or engine == "minted"
        )
        parts.append(
            context.formatter.codeblock(
                code=code_text,
                language=language,
                lineno=False,
                filename=None,
                highlight=[],
                baselinestretch=baselinestretch,
                engine=engine,
                state=context.state,
            )
        )

    return "\n\n".join(parts) + ("\n" if parts else "")


@renders(
    "pre",
    phase=RenderPhase.PRE,
    priority=10,
    name="exam_strip_fenced_code",
    before=("preformatted_code", "pre_code_blocks"),
)
def strip_fenced_code_in_pre(element: Tag, context: RenderContext) -> None:
    """Strip ``` fences from preformatted code blocks when present."""
    if element is None or not hasattr(element, "find"):
        return
    code_element = element.find("code")
    if code_element is None:
        return
    segments = _split_fenced_block(code_element.get_text(strip=False))
    if not segments:
        return
    latex = _render_fenced_segments(segments, context)
    if not latex:
        return
    context.suppress_children(element)
    element.replace_with(mark_processed(NavigableString(latex)))


@renders(
    "div",
    phase=RenderPhase.PRE,
    priority=10,
    name="exam_strip_fenced_code_blocks",
    before=("code_blocks",),
)
def strip_fenced_code_in_blocks(element: Tag, context: RenderContext) -> None:
    """Strip ``` fences from highlighted code blocks before rendering."""
    if element is None or not hasattr(element, "get"):
        return
    classes = element.get("class") or []
    if "highlight" not in classes and "codehilite" not in classes:
        return

    code_element = element.find("code")
    if code_element is None:
        return
    segments = _split_fenced_block(code_element.get_text(strip=False))
    if not segments:
        return
    latex = _render_fenced_segments(segments, context)
    if not latex:
        return
    context.suppress_children(element)
    element.replace_with(mark_processed(NavigableString(latex)))


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

    choice_style = _choice_style(context)
    if choice_style == "checkbox":
        lines = ["\\begin{samepage}", "\\begin{columen}[5]", "\\begin{checkboxes}"]
    else:
        lines = ["\\begin{samepage}", "\\begin{columen}[5]", "\\begin{choices}"]
    correct_labels: list[str] = []
    for index, (checked, text) in enumerate(items):
        if checked:
            lines.append(f"\\CorrectChoice {text}")
            correct_labels.append(_choice_label(index))
        else:
            lines.append(f"\\choice {text}")
    if choice_style == "checkbox":
        lines.append("\\end{checkboxes}")
        lines.append("\\end{columen}")
        lines.append("\\end{samepage}")
    else:
        lines.append("\\end{choices}")
        lines.append("\\end{columen}")
        if _in_solution_mode(context) and correct_labels:
            lines.append(f"\\answerline[{', '.join(correct_labels)}]")
        else:
            lines.append("\\answerline")
        lines.append("\\end{samepage}")

    element.replace_with(mark_processed(NavigableString("\n".join(lines) + "\n")))


@renders(
    "img",
    phase=RenderPhase.POST,
    priority=120,
    name="exam_images",
    nestable=False,
)
def render_exam_images(element: Tag, context: RenderContext) -> None:
    """Ensure images inside solution/admonition blocks render in LaTeX."""
    _render_images(element, context)


@renders(
    "p",
    phase=RenderPhase.POST,
    priority=80,
    name="exam_image_paragraphs",
    nestable=True,
    auto_mark=False,
)
def render_exam_image_paragraphs(element: Tag, context: RenderContext) -> None:
    """Unwrap paragraphs that only contain images so they render correctly."""
    if element.get("class"):
        return
    content_nodes = [
        node
        for node in element.contents
        if not (isinstance(node, NavigableString) and not node.strip())
    ]
    if not content_nodes:
        return
    if not all(isinstance(node, Tag) and node.name == "img" for node in content_nodes):
        return
    for img in list(element.find_all("img", recursive=False)):
        _render_images(img, context)
    element.unwrap()
    context.mark_processed(element, phase=RenderPhase.POST)


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
    grid_value = None
    if attrs:
        lines_match = _LINES_PATTERN.search(attrs)
        if lines_match:
            lines_value = lines_match.group(1)
        grid_match = _GRID_PATTERN.search(attrs)
        if grid_match:
            grid_value = grid_match.group(1)

    begin_env, end_env = _solution_env(lines_value, grid_value, _text_style(context))

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
    "texsmith-callout",
    phase=RenderPhase.POST,
    priority=130,
    name="exam_solution_callouts",
    after_children=True,
    before=("finalize_callouts",),
    nestable=False,
    auto_mark=False,
)
def render_solution_callouts(element: Tag, context: RenderContext) -> None:
    """Convert solution callouts into exam.cls solution environments."""
    classes = gather_classes(element.get("class"))
    title = element.attrs.pop("data-callout-title", "")
    is_solution = (
        "solution" in classes
        or "texsmith-solution" in classes
        or title.strip().lower() == "solution"
    )
    if not is_solution:
        return

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
    for key in ("lines", "grid"):
        if key in element.attrs:
            attr_values.append(f"{key}={element.attrs[key]}")
    if attr_values:
        attrs = ",".join([attrs, *attr_values]).strip(",")

    lines_value = None
    grid_value = None
    if attrs:
        lines_match = _LINES_PATTERN.search(attrs)
        if lines_match:
            lines_value = lines_match.group(1)
        grid_match = _GRID_PATTERN.search(attrs)
        if grid_match:
            grid_value = grid_match.group(1)

    for img in list(element.find_all("img")):
        _render_images(img, context)

    begin_env, end_env = _solution_env(lines_value, grid_value, _text_style(context))
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


@renders(
    "div",
    phase=RenderPhase.POST,
    priority=45,
    name="exam_solution_div_admonitions",
    nestable=True,
    auto_mark=False,
)
def render_solution_div_admonitions(element: Tag, context: RenderContext) -> None:
    """Convert solution divs before generic callout handling."""
    classes = gather_classes(element.get("class"))
    if "texsmith-solution" not in classes:
        return
    render_solution_callouts(element, context)


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
    if not empty_title:
        rendered_clean = text.replace("\\", "").strip()
        if _EMPTY_TITLE_PATTERN.fullmatch(rendered_clean) is not None:
            empty_title = True
            text = ""

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
        register_fn(set_exam_callouts)
        register_fn(strip_fenced_code_in_blocks)
        register_fn(strip_fenced_code_in_pre)
        register_fn(render_exam_checkboxes)
        register_fn(render_exam_image_paragraphs)
        register_fn(render_exam_images)
        register_fn(render_solution_admonition)
        register_fn(render_solution_div_admonitions)
        register_fn(render_solution_callouts)
        register_fn(render_exam_headings)
        register_fn(close_open_parts)

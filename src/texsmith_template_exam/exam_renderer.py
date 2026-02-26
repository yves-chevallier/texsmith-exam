"""Exam-specific LaTeX heading renderer for TeXSmith."""

from __future__ import annotations

from pathlib import Path
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from slugify import slugify
from texsmith.adapters.handlers._helpers import coerce_attribute, mark_processed
from texsmith.adapters.handlers.admonitions import gather_classes
from texsmith.adapters.handlers.blocks import _prepare_rich_text_content
from texsmith.adapters.handlers.code import _is_ascii_art, _resolve_code_engine
from texsmith.adapters.handlers.inline import _payload_is_block_environment
from texsmith.adapters.handlers.media import render_images as _render_images
from texsmith.adapters.markdown import render_markdown
from texsmith.core.callouts import DEFAULT_CALLOUTS, merge_callouts, normalise_callouts
from texsmith.core.context import RenderContext
from texsmith.core.rules import DOCUMENT_NODE, RenderPhase, renders
from texsmith.fonts.scripts import render_moving_text

from texsmith_template_exam.exam.fillin import build_fillin_latex, compute_fillin_width
from texsmith_template_exam.markdown import exam_markdown_extensions
from texsmith_template_exam.exam.utils import (
    choice_label,
    expand_lines_value,
    extract_dash_attrs_prefix,
    is_empty_title,
    is_truthy_attribute,
    matches_empty_title_pattern,
    normalize_answer_text,
    normalize_box_dim,
    normalize_points,
    normalize_style_choice,
    parse_heading_attrs,
)


_FILLIN_PATTERN = re.compile(r"\[([^\]\n]+)\](?!\()(?:\\?\{([^}\n]+)\\?\})?")

# Backwards-compatible aliases for tests and external callers.
_normalize_answer_text = normalize_answer_text
_extract_dash_attrs_prefix = extract_dash_attrs_prefix
_parse_heading_attrs = parse_heading_attrs
_choice_label = choice_label


def _flag(context: RenderContext, key: str) -> bool:
    return bool(context.state.counters.get(key, 0))


def _set_flag(context: RenderContext, key: str, value: bool) -> None:
    context.state.counters[key] = 1 if value else 0


def _ensure_solution_callout(context: RenderContext) -> None:
    callouts = context.runtime.get("callouts_definitions")
    merged = dict(callouts) if isinstance(callouts, dict) else merge_callouts(DEFAULT_CALLOUTS)
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
def set_exam_callouts(_root: Tag, context: RenderContext) -> None:
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
    return normalized in {"-", "–", "—"}


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
_LINES_PATTERN = re.compile(r"\blines\s*=\s*([^\s,}]+)\b")
_GRID_PATTERN = re.compile(r"\bgrid\s*=\s*([^\s,}]+)\b")
_BOX_PATTERN = re.compile(r"\bbox\s*=\s*([^\s,}]+)\b")
_ATTRS_BLOCK_PATTERN = re.compile(r"\\?\{(?P<attrs>[^}]*)\\?\}\s*$")
_HEADING_DASH_ATTRS_PATTERN = re.compile(r"^\s*-\s*\\?\{(?P<attrs>.*)\\?\}\s*$")


def _exam_style(context: RenderContext) -> dict[str, object]:
    overrides = context.runtime.get("template_overrides")
    if not isinstance(overrides, dict):
        return {}
    style = overrides.get("style")
    return style if isinstance(style, dict) else {}


def _in_solution_mode(context: RenderContext) -> bool:
    def _is_truthy(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        value = overrides.get("solution")
        if _is_truthy(value):
            return True
        press = overrides.get("press")
        if isinstance(press, dict) and _is_truthy(press.get("solution")):
            return True
    value = context.runtime.get("solution")
    if _is_truthy(value):
        return True

    front_matter_value = _front_matter_flag(context, ("solution", "exam.solution", "press.solution"))
    if _is_truthy(front_matter_value):
        return True

    # Fallback for project solution builds when overrides are not propagated.
    document_path = context.runtime.get("document_path")
    if document_path is not None:
        path_text = str(document_path).replace("\\", "/").lower()
        if "/solution/" in path_text or path_text.endswith("-solutions.md") or ".solution." in path_text:
            return True
    return False


def _in_compact_mode(context: RenderContext) -> bool:
    def _is_truthy(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        value = overrides.get("compact")
        if _is_truthy(value):
            return True
        press = overrides.get("press")
        if isinstance(press, dict) and _is_truthy(press.get("compact")):
            return True
    value = context.runtime.get("compact")
    if _is_truthy(value):
        return True

    front_matter_value = _front_matter_flag(context, ("compact", "exam.compact", "press.compact"))
    if _is_truthy(front_matter_value):
        return True

    # Fallback for project light builds where compact mode is generated in a
    # dedicated source directory before front-matter overrides are propagated.
    document_path = context.runtime.get("document_path")
    if document_path is not None:
        path_text = str(document_path).replace("\\", "/").lower()
        if "/light-src/" in path_text or path_text.endswith("-light.md") or ".light." in path_text:
            return True
    return False


def _front_matter_flag(context: RenderContext, keys: tuple[str, ...]) -> object:
    cache_key = "_texsmith_front_matter"
    cached = context.runtime.get(cache_key)
    if cached is None:
        document_path = context.runtime.get("document_path")
        front_matter: dict[str, object] = {}
        if document_path is not None:
            try:
                from texsmith.adapters.markdown import split_front_matter

                raw = Path(document_path).read_text(encoding="utf-8")
                front_matter, _ = split_front_matter(raw)
            except Exception:
                front_matter = {}
        context.runtime[cache_key] = front_matter
        cached = front_matter
    if not isinstance(cached, dict):
        return None
    for key in keys:
        if "." in key:
            cursor: object = cached
            for part in key.split("."):
                if not isinstance(cursor, dict):
                    cursor = None
                    break
                cursor = cursor.get(part)
            if cursor is not None:
                return cursor
        else:
            if key in cached:
                return cached.get(key)
    return None


def _choice_style(context: RenderContext) -> str:
    style = _exam_style(context)
    return normalize_style_choice(
        style.get("choices"),
        default="alpha",
        aliases={"checkboxes": "checkbox", "check": "checkbox"},
    )


def _text_style(context: RenderContext) -> str:
    style = _exam_style(context)
    return normalize_style_choice(
        style.get("text"),
        default="dotted",
        aliases={"dots": "dotted", "dottedlines": "dotted", "line": "lines"},
    )


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
    text_style: str,
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


@renders(
    "div",
    phase=RenderPhase.PRE,
    priority=40,
    name="solution_math_blocks",
    nestable=False,
    auto_mark=False,
)
def render_solution_math_blocks(element: Tag, _context: RenderContext) -> None:
    """Convert math script tags early inside solution blocks."""
    classes = gather_classes(element.get("class"))
    if "texsmith-solution" not in classes:
        return
    _convert_math_scripts(element)


@renders(
    "script",
    phase=RenderPhase.PRE,
    priority=70,
    name="solution_math_scripts",
    nestable=False,
    auto_mark=False,
)
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
        if _payload_is_block_environment(payload):
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


@renders(
    "p",
    phase=RenderPhase.POST,
    priority=95,
    name="solution_math_paragraphs",
    nestable=False,
)
def render_solution_math_paragraphs(element: Tag, _context: RenderContext) -> None:
    """Preserve math script payloads inside paragraphs before they are flattened."""
    if not element.find("script"):
        return
    _convert_math_scripts(element)
    element.attrs["data-texsmith-latex"] = "true"


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


def _replace_fillin_placeholders(
    root: Tag,
    context: RenderContext,
    *,
    allow_latex_raw: bool = False,
    pattern: re.Pattern[str] = _FILLIN_PATTERN,
) -> None:
    """Replace [answer]{w=50} placeholders with exam.cls fill-ins."""
    legacy_accents = getattr(context.config, "legacy_latex_accents", False)
    for node in list(root.find_all(string=True)):
        if getattr(node, "processed", False) and not allow_latex_raw:
            continue
        text = str(node)
        if not text or pattern.search(text) is None:
            continue

        parent = node.parent
        skip = False
        while parent is not None:
            if getattr(parent, "name", None) in {"code", "pre", "script"}:
                skip = True
                break
            classes = gather_classes(getattr(parent, "get", lambda *_: None)("class"))
            if (not allow_latex_raw) and (
                "latex-raw" in classes or parent.get("data-texsmith-latex") == "true"
            ):
                skip = True
                break
            parent = getattr(parent, "parent", None)
        if skip:
            continue

        segments: list[NavigableString] = []
        cursor = 0
        for match in pattern.finditer(text):
            if match.start() > cursor:
                segments.append(NavigableString(text[cursor : match.start()]))
            answer_raw = match.group(1)
            attrs = match.group(2) or ""
            answer = render_moving_text(
                answer_raw,
                context,
                legacy_accents=legacy_accents,
                escape="\\" not in answer_raw,
            )
            latex = build_fillin_latex(
                answer_raw=answer_raw,
                answer_latex=answer,
                attrs=attrs,
                context=context,
                solution_mode=_in_solution_mode(context),
            )
            segments.append(mark_processed(NavigableString(latex)))
            cursor = match.end()
        if cursor < len(text):
            segments.append(NavigableString(text[cursor:]))

        if not segments:
            continue
        first = segments[0]
        node.replace_with(first)
        cursor_node = first
        for segment in segments[1:]:
            cursor_node.insert_after(segment)
            cursor_node = segment


@renders(
    DOCUMENT_NODE,
    phase=RenderPhase.PRE,
    priority=-5,
    name="exam_fillin_placeholders",
    before=("escape_plain_text",),
)
def render_fillin_placeholders(root: Tag, context: RenderContext) -> None:
    """Replace [answer]{w=50} placeholders with exam.cls fill-ins."""
    _replace_fillin_placeholders(
        root,
        context,
        allow_latex_raw=False,
        pattern=_FILLIN_PATTERN,
    )


@renders(
    "td",
    "th",
    phase=RenderPhase.PRE,
    priority=-10,
    name="exam_table_fillin_cells",
    auto_mark=False,
)
def render_table_fillin_cells(element: Tag, context: RenderContext) -> None:
    """Handle placeholders in table cells even when inline code split the node."""
    raw = element.get_text(strip=False).strip()
    if not raw:
        return
    match = _FILLIN_PATTERN.fullmatch(raw)
    if not match:
        return

    attrs = match.group(2) or ""
    if not attrs:
        return

    answer_raw = match.group(1)
    answer = render_moving_text(
        answer_raw,
        context,
        legacy_accents=getattr(context.config, "legacy_latex_accents", False),
        escape=True,
    )
    latex = build_fillin_latex(
        answer_raw=answer_raw,
        answer_latex=answer,
        attrs=attrs,
        context=context,
        solution_mode=_in_solution_mode(context),
    )
    element.clear()
    element.append(mark_processed(NavigableString(latex)))


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
    show_answerline = not _in_compact_mode(context)
    correct_labels: list[str] = []
    for index, (checked, text) in enumerate(items):
        if checked:
            lines.append(f"\\CorrectChoice {text}")
            correct_labels.append(choice_label(index))
        else:
            lines.append(f"\\choice {text}")
    if choice_style == "checkbox":
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


@renders(
    "span",
    phase=RenderPhase.POST,
    priority=60,
    name="exam_fillin",
    nestable=True,
    auto_mark=False,
)
def render_exam_fillin(element: Tag, context: RenderContext) -> None:
    """Render inline fill-in blanks from Markdown placeholders."""
    classes = gather_classes(element.get("class"))
    if "texsmith-fillin" not in classes:
        return

    raw_text = element.get_text(strip=False)
    answer = render_moving_text(
        raw_text,
        context,
        legacy_accents=getattr(context.config, "legacy_latex_accents", False),
        escape="\\" not in raw_text,
    )
    attrs = ""
    if element.get("data-width"):
        attrs = f"width={element.get('data-width')}"
    elif element.get("data-scale"):
        attrs = f"char-width-scale={element.get('data-scale')}"
    width_value = compute_fillin_width(
        answer_raw=raw_text,
        attrs=attrs,
        context=context,
    )
    if _in_solution_mode(context):
        latex = f"\\fillin[{answer}]"
    else:
        latex = f"\\fillin[{answer}][{width_value}]"
    element.replace_with(mark_processed(NavigableString(latex)))


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
    priority=75,
    name="exam_pending_answerline_paragraph",
    nestable=True,
    auto_mark=False,
)
def render_pending_answerline_paragraph(element: Tag, context: RenderContext) -> None:
    pending = context.runtime.get("pending_question_answerline")
    if not pending:
        return
    if not element.get_text(strip=True):
        return
    element.insert_after(mark_processed(NavigableString("\n" + pending + "\n")))
    context.runtime["pending_question_answerline"] = None


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
        _text_style(context),
        compact_mode=_in_compact_mode(context),
        solution_mode=_in_solution_mode(context),
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
        _render_images(img, context)

    begin_env, end_env = _solution_env(
        lines_value,
        grid_value,
        box_value,
        _text_style(context),
        compact_mode=_in_compact_mode(context),
        solution_mode=_in_solution_mode(context),
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


@renders(
    "div",
    phase=RenderPhase.POST,
    priority=40,
    name="exam_solution_admonitions",
    nestable=True,
    auto_mark=False,
)
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
    heading_attrs: dict[str, str] = {}
    stripped_heading = raw_text.strip()
    attrs_match = _ATTRS_BLOCK_PATTERN.search(stripped_heading)
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
    if not heading_attrs:
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
    answer_text = normalize_answer_text(
        coerce_attribute(element.get("answer"))
        or coerce_attribute(element.get("data-answer"))
        or heading_attrs.get("answer")
    )
    answerline = (
        _answerline_latex(answer_text, context)
        if (answer_text and not _in_compact_mode(context))
        else None
    )
    defer_answerline = bool(answerline and _should_defer_answerline_for_heading_text(raw_text))
    if not ref:
        slug = slugify(plain_text, separator="-")
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
            latex = "\n".join(lines + [latex])
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
        register_fn(render_solution_math_blocks)
        register_fn(render_solution_math_paragraphs)
        register_fn(render_fillin_placeholders)
        register_fn(render_table_fillin_cells)
        register_fn(strip_fenced_code_in_blocks)
        register_fn(strip_fenced_code_in_pre)
        register_fn(render_exam_checkboxes)
        register_fn(render_exam_fillin)
        register_fn(render_pending_answerline_paragraph)
        register_fn(render_exam_image_paragraphs)
        register_fn(render_exam_images)
        register_fn(render_solution_admonition)
        register_fn(promote_solution_admonitions)
        register_fn(render_solution_div_admonitions)
        register_fn(render_solution_callouts)
        register_fn(render_exam_headings)
        register_fn(close_open_parts)

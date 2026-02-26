"""Helpers to render fenced code segments inside exam templates."""

from __future__ import annotations

from bs4.element import NavigableString, Tag
from texsmith_template_exam.exam.texsmith_compat import (
    is_ascii_art,
    mark_processed,
    resolve_code_engine,
)
from texsmith.core.context import RenderContext
from texsmith.fonts.scripts import render_moving_text


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
    engine = resolve_code_engine(context)

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
        baselinestretch = 0.5 if is_ascii_art(code_text) else None
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


__all__ = ["strip_fenced_code_in_blocks", "strip_fenced_code_in_pre"]

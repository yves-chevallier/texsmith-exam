"""Render a slice of IR through tmark's writer.

A construct such as ``\\titledquestion{…}`` or ``\\choice …`` takes *markup*
where the author wrote inline Markdown, so the pass has to write that slice
itself. It does so through the same writer as the body — a one-block synthetic
document handed to ``tmark.write`` — rather than reimplementing escaping,
emphasis and inline code. The backend is a parameter, so the Typst emitter
reuses this module unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable

import tmark
from tmark.ir import codec, model


_EMPTY_SPAN = model.Span(file=0, start=0, end=0)


def _empty_front_matter() -> model.FrontMatter:
    """The front matter of an empty document — the records tmark's codec expects."""
    return codec.decode_document(tmark.parse("")).front_matter


_FRONT_MATTER = _empty_front_matter()


def _write(blocks: tuple[model.Block, ...], backend: str) -> str:
    if not blocks:
        return ""
    document = model.Document(blocks=blocks, file=0, front_matter=_FRONT_MATTER)
    payload = codec.encode_document(document)
    return str(tmark.write(payload, backend, {}).get("text") or "")


def render_inlines(nodes: Iterable[model.Inline], backend: str = "latex") -> str:
    """``nodes`` as backend markup, without a trailing paragraph break."""
    content = tuple(nodes)
    if not content:
        return ""
    plain = model.Plain(id=0, span=_EMPTY_SPAN, content=content)
    return _write((plain,), backend).strip()


def render_blocks(blocks: Iterable[model.Block], backend: str = "latex") -> str:
    """``blocks`` as backend markup."""
    return _write(tuple(blocks), backend).strip()


def render_item(blocks: Iterable[model.Block], backend: str = "latex") -> str:
    """A list item's body: its inlines when it is a single paragraph, else its blocks.

    A multiple-choice entry is one short paragraph, and ``\\choice`` takes it
    inline; anything richer keeps its block structure.
    """
    content = tuple(blocks)
    if len(content) == 1 and isinstance(content[0], (model.Para, model.Plain)):
        return render_inlines(content[0].content, backend)
    return render_blocks(content, backend)


def plain_text(nodes: Iterable[model.Node]) -> str:
    """The text an inline run carries, spaces included — used to size a blank."""
    parts: list[str] = []
    for node in nodes:
        text = getattr(node, "text", None)
        if isinstance(text, str):
            parts.append(text)
            continue
        if isinstance(node, model.Space):
            parts.append(" ")
            continue
        content = getattr(node, "content", None)
        if isinstance(content, tuple):
            parts.append(plain_text(content))
    return "".join(parts)


__all__ = ["plain_text", "render_blocks", "render_inlines", "render_item"]

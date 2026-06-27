"""Markdown extension turning ``[answer]{w=…}`` blanks into fill-in spans.

Runs as a low-priority inline processor so genuine links (`[text](url)`),
reference links and footnotes are claimed by their own processors first; only a
literal ``[answer]`` (not immediately followed by ``(``) becomes a fill-in. The
emitted ``<span class="texsmith-fillin">`` is lowered to an ``exam-fillin`` IR
node by :mod:`texsmith_template_exam.reader` and rendered as ``\\fillin`` by the
exam writer — replacing the old post-HTML text-scanning renderers.
"""

from __future__ import annotations

import xml.etree.ElementTree as etree  # noqa: N813

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


# [answer] not followed by "(" (so inline links are left alone), with an
# optional {…} attribute block (e.g. {w=50} or {char-width-scale=3}).
_FILLIN_RE = r"\[([^\]\n]+)\](?!\()(?:\{([^}\n]+)\})?"


class _FillinInlineProcessor(InlineProcessor):
    def handleMatch(self, match, data) -> tuple[etree.Element, int, int]:  # noqa: ANN001, N802
        answer = match.group(1)
        attrs = match.group(2) or ""
        element = etree.Element("span")
        element.set("class", "texsmith-fillin")
        if attrs:
            element.set("data-attrs", attrs)
        element.text = answer
        return element, match.start(0), match.end(0)


class FillinExtension(Extension):
    """Register the fill-in inline processor."""

    def extendMarkdown(self, md: Markdown) -> None:  # type: ignore[override]  # noqa: N802
        md.inlinePatterns.register(
            _FillinInlineProcessor(_FILLIN_RE, md),
            "texsmith_exam_fillin",
            5,
        )


def makeExtension(**kwargs: object) -> FillinExtension:  # noqa: N802
    return FillinExtension(**kwargs)


__all__ = ["FillinExtension", "makeExtension"]

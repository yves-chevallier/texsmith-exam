"""Shared helpers: run the ``exam`` pass over a snippet, or a whole conversion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from texsmith.core.documents import Document
from texsmith.passes import PassContext
import tmark
from tmark.ir import codec

from texsmith_template_exam.passes.exam import run as exam_pass


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "src/texsmith_template_exam/exam"


def parse(markdown: str) -> Document:
    """A :class:`Document` holding the IR of ``markdown``, as a conversion would."""
    ir = codec.decode_document(tmark.parse(markdown))
    return Document(source_path=Path("<memory>.md"), _front_matter={}, ir=ir)


def run_pass(markdown: str, **attributes: Any) -> Document:
    """Parse ``markdown`` and run the exam pass with ``attributes`` as overrides."""
    ctx = PassContext(contexts=(attributes,))
    ctx.ids.observe(parse(markdown).ir)
    return exam_pass(parse(markdown), ctx)


def latex(markdown: str, **attributes: Any) -> str:
    """The LaTeX body of ``markdown`` once the exam pass has rewritten it."""
    document = run_pass(markdown, **attributes)
    payload = codec.encode_document(document.ir)
    return str(tmark.write(payload, "latex", {}).get("text") or "")


@pytest.fixture
def exam_latex():
    """``exam_latex(markdown, **attributes)`` — the rewritten LaTeX body."""
    return latex

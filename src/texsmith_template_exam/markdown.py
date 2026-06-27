"""Template-scoped Markdown extension helpers."""

from __future__ import annotations

from texsmith.adapters.markdown import (
    DEFAULT_MARKDOWN_EXTENSIONS,
    deduplicate_markdown_extensions,
)


SOLUTION_EXTENSION = "texsmith_template_exam.solution_md:SolutionAdmonitionExtension"
FILLIN_EXTENSION = "texsmith_template_exam.fillin_md:FillinExtension"


def exam_markdown_extensions() -> list[str]:
    """Return the Markdown extensions with the exam solution + fill-in blocks enabled."""
    return deduplicate_markdown_extensions(
        [*DEFAULT_MARKDOWN_EXTENSIONS, SOLUTION_EXTENSION, FILLIN_EXTENSION]
    )

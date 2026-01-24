"""Template-scoped Markdown extension helpers."""

from __future__ import annotations

from texsmith.adapters.markdown import DEFAULT_MARKDOWN_EXTENSIONS, deduplicate_markdown_extensions


SOLUTION_EXTENSION = "texsmith_template_exam.solution_md:SolutionAdmonitionExtension"


def exam_markdown_extensions() -> list[str]:
    """Return the Markdown extensions with the exam solution block enabled."""
    if SOLUTION_EXTENSION not in DEFAULT_MARKDOWN_EXTENSIONS:
        DEFAULT_MARKDOWN_EXTENSIONS.append(SOLUTION_EXTENSION)
    return deduplicate_markdown_extensions(DEFAULT_MARKDOWN_EXTENSIONS)

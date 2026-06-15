"""Template-scoped Markdown extension helpers."""

from __future__ import annotations

from texsmith.adapters.markdown import (
    DEFAULT_MARKDOWN_EXTENSIONS,
    deduplicate_markdown_extensions,
)


SOLUTION_EXTENSION = "texsmith_template_exam.solution_md:SolutionAdmonitionExtension"
HEADING_ATTR_LIST_EXTENSION = "texsmith_template_exam.heading_attr_list_md:HeadingAttrListExtension"


def exam_markdown_extensions() -> list[str]:
    """Return the Markdown extensions with the exam solution block enabled."""
    return deduplicate_markdown_extensions(
        [*DEFAULT_MARKDOWN_EXTENSIONS, HEADING_ATTR_LIST_EXTENSION, SOLUTION_EXTENSION]
    )

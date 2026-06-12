import markdown

from texsmith_template_exam.markdown import (
    HEADING_ATTR_LIST_EXTENSION,
    SOLUTION_EXTENSION,
    exam_markdown_extensions,
)


def test_exam_markdown_extensions_includes_solution_extension() -> None:
    extensions = exam_markdown_extensions()
    assert SOLUTION_EXTENSION in extensions


def test_exam_markdown_extensions_includes_heading_attr_list_extension() -> None:
    extensions = exam_markdown_extensions()
    assert HEADING_ATTR_LIST_EXTENSION in extensions


def test_exam_markdown_extensions_is_idempotent() -> None:
    first = exam_markdown_extensions()
    second = exam_markdown_extensions()

    assert first == second
    assert first.count(SOLUTION_EXTENSION) == 1
    assert first.count(HEADING_ATTR_LIST_EXTENSION) == 1


def _render(source: str) -> str:
    return markdown.markdown(source, extensions=exam_markdown_extensions())


def test_heading_attrs_survive_double_quoted_value() -> None:
    # Regression: the smart-quote inline processor used to rewrite ``"20"`` into
    # a ``<q>`` element before ``attr_list`` could read the heading attribute
    # block, dropping ``points``/``answer`` entirely.
    html = _render('## `printf("%d ", a[1])` { points=1 answer="20" }')

    assert 'points="1"' in html
    assert 'answer="20"' in html
    assert "{ points" not in html  # the literal block must be consumed
    assert "<q>" not in html  # the value must not be smart-quoted


def test_heading_attrs_double_quoted_value_with_spaces() -> None:
    html = _render('## Title { points=2 answer="hello world" }')

    assert 'points="2"' in html
    assert 'answer="hello world"' in html


def test_heading_attrs_double_quoted_value_with_apostrophe() -> None:
    html = _render("## Title { points=1 answer=\"l'index\" }")

    assert 'points="1"' in html
    assert "answer=\"l'index\"" in html


def test_heading_attrs_unquoted_value_still_works() -> None:
    html = _render("## `code` { points=1 answer=20 }")

    assert 'points="1"' in html
    assert 'answer="20"' in html


def test_heading_attrs_preserve_id_and_class() -> None:
    html = _render("## Ref { #myid .myclass points=3 }")

    assert 'id="myid"' in html
    assert 'myclass' in html
    assert 'points="3"' in html


def test_heading_without_attr_block_keeps_smart_quotes() -> None:
    # Body-text double quotes (no trailing attribute block) must still become a
    # semantic ``<q>`` element and must not be mistaken for an attribute list.
    html = _render('## not really "an attr block" here')

    assert "<q>an attr block</q>" in html
    assert "answer=" not in html

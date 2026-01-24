from markdown import Markdown

from texsmith_template_exam.solution_md import SolutionAdmonitionExtension


def _render(text: str) -> str:
    md = Markdown(extensions=[SolutionAdmonitionExtension()])
    return md.convert(text)


def test_solution_admonition_wraps_content_with_attrs() -> None:
    source = """\
!!! solution { lines=2 }
    This is the solution.
    Second line.
"""
    html = _render(source)

    assert 'class="texsmith-solution"' in html
    assert 'lines="2"' in html
    assert 'class="texsmith-solution-title"' in html
    assert "This is the solution." in html
    assert "Second line." in html


def test_solution_admonition_ignores_empty_block() -> None:
    source = "!!! solution\n"
    html = _render(source)

    assert "texsmith-solution" not in html

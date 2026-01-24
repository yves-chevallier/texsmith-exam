from texsmith_template_exam.markdown import SOLUTION_EXTENSION, exam_markdown_extensions


def test_exam_markdown_extensions_includes_solution_extension() -> None:
    extensions = exam_markdown_extensions()
    assert SOLUTION_EXTENSION in extensions


def test_exam_markdown_extensions_is_idempotent() -> None:
    first = exam_markdown_extensions()
    second = exam_markdown_extensions()

    assert first == second
    assert first.count(SOLUTION_EXTENSION) == 1

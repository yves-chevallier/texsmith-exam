"""End-to-end rendering tests for the exam reader/writer (texsmith 0.4.x IR)."""

from __future__ import annotations

from texsmith.adapters.latex.renderer import LaTeXRenderer
from texsmith.adapters.markdown import render_markdown
from texsmith.readers.html import build_reader_registry

from texsmith_template_exam import reader as exam_reader
from texsmith_template_exam.markdown import exam_markdown_extensions
from texsmith_template_exam.writer import ExamLaTeXWriter


def _render(md: str, *, runtime: dict | None = None) -> str:
    renderer = LaTeXRenderer()
    renderer.reader_registry = build_reader_registry([exam_reader])
    renderer.writer_class = ExamLaTeXWriter
    html = render_markdown(md, exam_markdown_extensions()).html
    return renderer.render(html, runtime=runtime or {})


# -- multiple choice -------------------------------------------------------


def test_multiple_choice_becomes_choices_with_answerline() -> None:
    latex = _render("- [ ] Wrong\n- [x] Right\n- [ ] Other\n")
    assert "\\begin{choices}" in latex
    assert "\\CorrectChoice Right" in latex
    assert "\\choice Wrong" in latex
    assert "\\answerline[B]" in latex


def test_ordinary_list_is_not_a_choices_block() -> None:
    latex = _render("- apples\n- pears\n")
    assert "choices" not in latex
    assert "itemize" in latex


# -- fill-ins --------------------------------------------------------------


def test_fillin_explicit_width() -> None:
    assert "\\fillin[Paris][30mm]" in _render("Capital: [Paris]{w=30}.")


def test_fillin_auto_width() -> None:
    assert "\\fillin[Paris][12.5mm]" in _render("Capital: [Paris].")


def test_real_link_is_not_a_fillin() -> None:
    latex = _render("See [docs](https://example.com).")
    assert "\\fillin" not in latex
    assert "href" in latex


def test_code_fillin_answer_is_fully_escaped() -> None:
    # A code answer carrying both a backslash and a percent must be fully
    # escaped; an unescaped % would comment out the \fillin closing bracket and
    # abort compilation ("Paragraph ended before \fillin was complete").
    latex = _render('Y [`printf("%.2lf\\n")`]{w=2cm}')
    assert '\\fillin[printf("\\%.2lf\\textbackslash{}n")][2cm]' in latex
    assert "%.2lf" not in latex.replace("\\%.2lf", "")  # no bare % survives


def test_plain_text_fillin_answer_keeps_raw_latex() -> None:
    # A plain-text answer containing a backslash is treated as raw LaTeX (the
    # heuristic), so authors can still write a command in a fill-in answer.
    latex = _render("W [\\textbf{x}]{w=2cm}")
    assert "\\fillin[\\textbf{x}][2cm]" in latex


# -- headings -> questions / parts -----------------------------------------


# The exam template renders body slots with base_level=1 (so an H1 maps to a
# top-level \question); mimic that here since a bare renderer defaults to 0.
_LVL1 = {"base_level": 1}


def test_titled_question_and_parts() -> None:
    latex = _render("# Intro { points=5 }\n\n## -\n\nFirst\n\n## -\n\nSecond\n", runtime=_LVL1)
    assert "\\titledquestion{Intro}[5]" in latex
    assert "\\begin{parts}" in latex
    assert latex.count("\\part") >= 2
    assert "\\end{parts}" in latex


def test_nested_subparts_open_and_close() -> None:
    latex = _render("# -\n\n## -\n\n### -\n\n#### -\n", runtime=_LVL1)
    assert "\\begin{parts}" in latex
    assert "\\begin{subparts}" in latex
    assert "\\begin{subsubparts}" in latex
    assert "\\end{subsubparts}" in latex
    assert "\\end{subparts}" in latex
    assert "\\end{parts}" in latex


def test_plain_heading_via_heading_attribute() -> None:
    latex = _render("# Section { heading=true }\n\nBody\n", runtime=_LVL1)
    assert "\\titledquestion" not in latex
    assert "\\chapter" in latex or "\\section" in latex


# -- solutions -------------------------------------------------------------


def test_solution_block_dotted_lines() -> None:
    latex = _render("## -\n\nQ?\n\n!!! solution { lines=2 }\n    The answer.\n")
    assert "\\begin{solutionordottedlines}[2\\dottedlinefillheight]" in latex
    assert "The answer." in latex
    assert "\\end{solutionordottedlines}" in latex


def test_solution_grid() -> None:
    latex = _render("## -\n\nQ?\n\n!!! solution { grid=5 }\n    Work here.\n")
    assert "\\begin{solutionorgrid}[5\\linefillheight]" in latex

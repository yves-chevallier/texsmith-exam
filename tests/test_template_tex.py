from __future__ import annotations

from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "src/texsmith_template_exam/exam/template/template.tex"


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_supports_problem_label_override() -> None:
    text = _template_text()
    assert "problem-label" in text
    assert "problem_label" in text


def test_template_supports_french_thin_colon_space() -> None:
    text = _template_text()
    assert r"\frenchsetup{ThinColonSpace=true}" in text


def test_template_supports_fillin_solution_underline_option() -> None:
    text = _template_text()
    assert "fillin_solution_underline" in text
    assert "fillin-solution-underline" in text
    assert r"\newif\iftexsmithfillinsolutionunderline" in text


def test_template_contains_code_spacing_tuning() -> None:
    text = _template_text()
    assert "before skip=-0.95\\baselineskip" in text
    assert "after skip=0.4\\baselineskip" in text
    assert r"\if@inlabel\else\vspace{0.5em}\fi" in text
    assert r"\needspace{6\baselineskip}" in text


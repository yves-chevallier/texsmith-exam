from __future__ import annotations

from pathlib import Path


TEMPLATE = (
    Path(__file__).resolve().parents[1] / "src/texsmith_template_exam/exam/template/template.tex"
)


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


def test_template_restyles_the_tscode_contract() -> None:
    # texsmith 0.8: the writer emits ``tscode``, not the old ``code`` box.
    text = _template_text()
    assert r"\tcbset{/ts/code/.append style={" in text
    assert "before skip=-0.95\\baselineskip" in text
    assert "after skip=0.4\\baselineskip" in text
    assert r"\BeforeBeginEnvironment{tscode}" in text
    assert r"\AfterEndEnvironment{tscode}{\par}" in text
    assert r"{code}" not in text.split("Contract macros")[1]


def test_template_defines_the_divider_as_a_page_break() -> None:
    assert r"\providecommand{\tsdivider}{\clearpage}" in _template_text()


def test_template_keeps_the_name_field_for_recto_pages() -> None:
    text = _template_text()
    assert r"\newcommand{\ExamNameField}" in text
    assert "recto_name_enabled" in text


def test_template_leaves_the_heig_logo_to_its_fragment() -> None:
    # The logo is the ``heiglogo`` fragment's; the template only places a
    # custom image file of its own.
    text = _template_text()
    assert r"\usepackage{heiglogo}" not in text
    assert r"\ExamLogoCustom" in text


def test_template_supports_version_display() -> None:
    text = _template_text()
    assert "version_value" in text
    assert "exam_version" in text
    assert "date_display" in text


def test_the_builtin_logo_is_sized_by_the_title_page_layout() -> None:
    # The heiglogo fragment calls \logo without a size, so it would draw at the
    # vintage default (18mm, the cover size) even on a `minimal' title page,
    # where the logo then runs into the header rule. The template hands the
    # geometry it resolved to the package instead.
    text = _template_text()
    assert r"\heiglogoSetup{height=\VAR{logo_height}}" in text
    setup = text.split(r"\heiglogoSetup")[0]
    # \@ifpackageloaded needs the letter catcode, and the guard must not fire
    # for a document that disabled the logo or brought a file of its own.
    assert setup.rsplit(r"\makeatletter", 1)[1].count(r"\makeatother") == 0
    assert r"\BLOCK{ if logo_builtin and not logo_disabled and logo_height }" in text

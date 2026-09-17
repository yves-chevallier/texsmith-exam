"""The Typst scaffolding: what ``template.typ`` has to provide, and its manifest."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "src/texsmith_template_exam/exam"
TEMPLATE = ROOT / "template/template.typ"
LOGOS = ROOT / "template/logos"


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_the_scaffolding_defines_the_exam_constructs() -> None:
    text = _template_text()
    for name in (
        "exam-question",
        "exam-part",
        "exam-subpart",
        "exam-subsubpart",
        "exam-choices",
        "exam-fillin",
        "exam-answerline",
        "exam-solution",
        "exam-reserve",
        "exam-grade-table",
    ):
        assert f"#let {name}(" in text, name


def test_the_scaffolding_restyles_the_contracts_after_the_prelude() -> None:
    text = _template_text()
    prelude = text.index("{{ prelude }}")
    body = text.index("{{ body }}")
    for override in ("#let ts-divider()", "#let ts-code(", "#let ts-task(", "#show raw.where("):
        assert prelude < text.index(override) < body, override


def test_a_thematic_break_is_a_page_break() -> None:
    assert "#let ts-divider() = pagebreak(weak: true)" in _template_text()


def test_the_reserved_line_has_the_pitch_of_exam_cls() -> None:
    # \dottedlinefillheight is 0.25in; the lines must line up with the LaTeX
    # ones or a page holds a different number of them.
    assert "#let exam-line-height = 18pt" in _template_text()


def test_the_scaffolding_knows_the_four_languages_template_tex_knows() -> None:
    text = _template_text()
    for label in ("Problème", "Aufgabe", "Problema", "Problem"):
        assert f'#let exam-problem-label = "{{{{ problem_label or \'{label}\' }}}}"' in text


def test_every_logo_vintage_is_shipped() -> None:
    from texsmith_template_exam.logo import VINTAGES

    for vintage in VINTAGES:
        library = LOGOS / f"heiglogo-{vintage}.typ"
        assert library.is_file(), vintage
        text = library.read_text(encoding="utf-8")
        assert "#let heig-logo-mono = \"<svg" in text
        assert "#let heig-logo-color = \"<svg" in text
        # The SVG is inlined in a Typst string: it must not carry a quote of
        # its own, and there is nothing to escape but that.
        assert '"' not in text.split("heig-logo-mono = ")[1].split("\n")[0][1:-1]


def test_the_vintage_follows_the_document_date() -> None:
    from texsmith_template_exam.logo import resolve_vintage

    assert resolve_vintage("2006-01-01") == "2004"
    assert resolve_vintage("2017-05-05") == "2009"
    assert resolve_vintage("2024-02-06") == "2020"
    assert resolve_vintage(None) == "2020"


def test_the_typst_section_mirrors_the_latex_attributes() -> None:
    from texsmith.core.templates.manifest import TemplateManifest

    manifest = TemplateManifest.load(ROOT / "template/manifest.toml")
    latex = set(manifest.section("latex").attributes)
    typst = set(manifest.section("typst").attributes)

    # What the Typst half adds: the date it formats itself, the logo the
    # `heiglogo` fragment draws on the LaTeX side, the two style keys
    # `template.tex` reads out of the `exam` mapping directly, and the subtitle
    # it reads as a bare context key.
    assert typst - latex == {
        "exam_date",
        "logo_color",
        "logo_vintage",
        "logo_year",
        "style_choices",
        "style_text",
        "subtitle",
    }
    # What it leaves out: `date` (renamed), the author it takes from the
    # renderer's own author views, and the LaTeX-only engine knobs.
    assert latex - typst == {"author", "date", "geometry", "hyperref_options"}

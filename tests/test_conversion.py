"""One small multi-file exam through the real pipeline, in both modes.

No PDF is built: the assertions are on the ``.tex`` the conversion writes, which
is what the template port is about. ``ConversionService`` is the same entry
point the CLI uses, so the template is loaded from its manifest, its declared
pass runs, its fragments are resolved and ``template.tex`` is rendered.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from texsmith.core.conversion import ConversionRequest
from texsmith.core.conversion.service import ConversionService
import yaml


QUESTIONS = """\
# Syntaxe { points=10 }

Considerez les bibliothèques comme déjà incluses.

## -

Écrire un message sur la sortie d'erreur.

::: solution {lines=3}

```cpp
std::cerr << "Erreur" << std::endl;
```
:::

## -

Le mot clef [virtual]{w=3cm} rend une méthode polymorphe.
"""

CHOICES = """\
# Choix multiples { points=5 }

## -

Quels sont les constituants implicites ?

- [ ] Un operateur de flux.
- [x] Un destructeur.
- [x] Un constructeur par copie.
"""

CONFIG = """\
title: Examen
subtitle: Test
author: Prof. Test
language: fr
exam:
  type: Examen
  department: TIN
  school: HEIG-VD
  course: Test
  duration: 60
  rules:
    preset: te
    standard: cpp17
"""


@pytest.fixture
def exam_sources(tmp_path: Path) -> tuple[Path, list[Path]]:
    """``(config.yml, [the two question files])`` — the shape the CLI is given."""
    config = tmp_path / "config.yml"
    config.write_text(CONFIG, encoding="utf-8")
    first = tmp_path / "1-syntaxe.md"
    first.write_text(QUESTIONS, encoding="utf-8")
    second = tmp_path / "2-qcm.md"
    second.write_text(CHOICES, encoding="utf-8")
    return config, [first, second]


def _convert(
    sources: tuple[Path, list[Path]], render_dir: Path, **options: Any
) -> dict[str, str]:
    config, documents = sources
    request = ConversionRequest(
        documents=documents,
        bibliography_files=[],
        # What the CLI does with a ``config.yml`` argument: shared front matter
        # for every document of the batch.
        front_matter=yaml.safe_load(config.read_text(encoding="utf-8")),
        front_matter_paths=[config],
        template="exam",
        render_dir=render_dir,
        template_options=options,
    )
    service = ConversionService()
    response = service.execute(request, prepared=service.prepare_documents(request))
    result = response.render_result
    written = {Path(result.main_tex_path).name: Path(result.main_tex_path).read_text("utf-8")}
    for path in render_dir.glob("*.tex"):
        written[path.name] = path.read_text(encoding="utf-8")
    return written


def test_the_exam_mode_reserves_the_answer_space(
    exam_sources: tuple[Path, list[Path]], tmp_path: Path
) -> None:
    written = _convert(exam_sources, tmp_path / "exam")

    syntax = written["1-syntaxe.tex"]
    assert r"\titledquestion{Syntaxe}[10]\label{syntaxe}" in syntax
    assert r"\begin{parts}" in syntax and syntax.rstrip().endswith(r"\end{parts}")
    assert r"\begin{solutionordottedlines}[3\dottedlinefillheight]" in syntax
    assert r"\fillin[virtual][3cm]" in syntax
    # The code fence still went through the highlight pass.
    assert r"\begin{tscode}[lang=cpp" in syntax

    qcm = written["2-qcm.tex"]
    assert r"\CorrectChoice Un destructeur." in qcm
    assert r"\ifprintanswers\answerline[B, C]\else\answerline\fi" in qcm

    main = written["main.tex"]
    assert r"\documentclass[a4paper,twoside,addpoints]{exam}" in main
    assert r"\printanswers" not in main
    assert r"\input{1-syntaxe.tex}" in main
    # The cover page still receives its context, rules preset expanded.
    assert r"\title{Examen}" in main
    assert "Rendre toutes les feuilles de ce travail écrit." in main
    assert "ISO/IEC 14882:2017" in main
    assert r"\gradetable[v][questions]" in main


def test_the_solution_mode_prints_the_answers(
    exam_sources: tuple[Path, list[Path]], tmp_path: Path
) -> None:
    written = _convert(exam_sources, tmp_path / "solution", solution=True)

    assert r"\printanswers" in written["main.tex"]
    syntax = written["1-syntaxe.tex"]
    # The reserved space is the same environment; exam.cls prints the body.
    assert r"\begin{solutionordottedlines}[3\dottedlinefillheight]" in syntax
    assert r"\par\smallskip" in syntax
    # A blank shows its answer without reserving a width.
    assert r"\fillin[virtual]" in syntax
    assert "3cm" not in syntax


def test_the_template_declares_its_pass_and_its_fragments() -> None:
    from texsmith.core.templates.runtime import load_template_runtime

    runtime = load_template_runtime("exam")
    info = runtime.instance.info

    assert [item.name for item in info.pass_specs()] == ["exam"]
    assert "heiglogo" in info.fragments
    assert "ts-todolist" in info.fragments
    assert info.engine == "lualatex"

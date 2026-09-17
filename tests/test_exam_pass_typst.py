"""The ``exam`` pass with ``backend="typst"``: the same snippets, Typst out.

The twin of :mod:`test_exam_pass`. What the pass *recognises* is tested there —
it is backend-neutral; what is checked here is the markup
:class:`~texsmith_template_exam.passes.typst.TypstEmitter` writes for each
construct, and that every call it makes is one ``template.typ`` defines.
"""

from __future__ import annotations

from pathlib import Path
import re

from conftest import run_pass, typst
from tmark.ir import model
from tmark.ir.walk import walk


TEMPLATE = (
    Path(__file__).resolve().parents[1] / "src/texsmith_template_exam/exam/template/template.typ"
)


# -- questions, parts, subparts -------------------------------------------


def test_a_top_level_heading_opens_a_question() -> None:
    body = typst("# Syntaxe { points=10 }\n\nConsiderez.\n")

    assert '#exam-question(points: "10", id: "syntaxe")[Syntaxe]' in body


def test_a_dash_heading_is_an_anonymous_part() -> None:
    body = typst("# Q\n\n## -\n\nFirst.\n\n## -\n\nSecond.\n")

    assert body.count("#exam-part()[]") == 2
    # No environment to close: a Typst level is a counter.
    assert "\\end" not in body


def test_points_reach_the_part() -> None:
    assert '#exam-part(points: "3")[]' in typst("# Q\n\n## - { points=3 }\n\nText.\n")


def test_points_are_dropped_when_points_are_disabled() -> None:
    body = typst("# Q { points=10 }\n\n## - { points=3 }\n\nText.\n", points=False)

    assert '#exam-question(id: "q")[Q]' in body
    assert "#exam-part()[]" in body


def test_the_three_depths_each_have_their_own_function() -> None:
    body = typst("# Q\n\n## -\n\nPart.\n\n### -\n\nSub.\n\n#### -\n\nSubsub.\n")

    assert "#exam-part()[]" in body
    assert "#exam-subpart()[]" in body
    assert "#exam-subsubpart()[]" in body


def test_a_heading_attribute_leaves_the_question_machinery() -> None:
    body = typst("# Q\n\n## Annexe { heading=true }\n\nText.\n")

    assert "== Annexe" in body
    assert "#exam-part" not in body


def test_newpage_breaks_the_page_before_the_question() -> None:
    body = typst("# Fonctions { points=15 newpage=true }\n\nText.\n")

    # A block, not an inline: Typst refuses a page break inside a paragraph.
    assert body.startswith("#pagebreak(weak: true)\n\n#exam-question(")


def test_an_answer_attribute_prints_an_answer_line_after_the_text() -> None:
    body = typst("# Q\n\n## - { points=1 answer=42 }\n\nWhat is it?\n")

    assert body.index("What is it?") < body.index("#exam-answerline(answer: [42])")


# -- multiple choice -------------------------------------------------------


def test_a_task_list_becomes_a_choices_call_with_the_correct_indices() -> None:
    body = typst("# Q\n\n## -\n\n- [ ] Wrong\n- [x] Right\n- [ ] Other\n- [x] Also\n")

    assert "#exam-choices(correct: (1, 3, ))[" in body
    # The choices are a Typst list: the one shape a marker with no closing
    # delimiter can make, and what `exam-choices` reads the items off.
    assert "\n- Wrong\n- Right\n- Other\n- Also\n]" in body


def test_a_task_list_without_a_correct_choice_still_calls_the_function() -> None:
    body = typst("# Q\n\n## -\n\n- [ ] One\n- [ ] Two\n")

    assert "#exam-choices(correct: ())[" in body


def test_a_plain_bullet_list_is_not_a_choices_block() -> None:
    body = typst("# Q\n\n## -\n\n- One\n- Two\n")

    assert "#exam-choices" not in body


def test_a_choice_body_keeps_its_inline_code_as_ir() -> None:
    document = run_pass("# Q\n\n## -\n\n- [x] `std::map`\n", backend="typst")

    assert any(isinstance(node, model.Code) for node in walk(document.ir))


# -- fill-in blanks --------------------------------------------------------


def test_a_span_with_a_width_becomes_a_fillin() -> None:
    assert "#exam-fillin(width: 3cm)[virtual]" in typst("# Q\n\nLe mot [virtual]{w=3cm} ici.\n")


def test_a_bare_width_is_read_as_millimetres() -> None:
    assert "#exam-fillin(width: 30mm)[x]" in typst("# Q\n\nA [x]{w=30} b.\n")


def test_a_fillin_without_a_width_is_sized_from_the_answer() -> None:
    assert "#exam-fillin(width: 12.5mm)[abcde]" in typst("# Q\n\nA [abcde]{.fillin} b.\n")


def test_solution_mode_prints_the_answer_and_reserves_nothing() -> None:
    body = typst("# Q\n\nLe mot [virtual]{w=3cm} ici.\n", solution=True)

    assert "#exam-fillin()[virtual]" in body
    assert "3cm" not in body


def test_a_bare_bracket_is_a_fillin_too() -> None:
    assert "#exam-fillin(width: 10mm)[path]" in typst("# Q\n\nThe [path] of it.\n")


# -- solution blocks -------------------------------------------------------


def test_a_solution_with_lines_reserves_that_many() -> None:
    body = typst("# Q\n\n::: solution {lines=3}\nAnswer.\n:::\n")

    assert "#exam-solution(lines: 3)[" in body
    assert "Answer." in body


def test_the_div_and_admonition_spellings_are_read_the_same_way() -> None:
    assert "#exam-solution(lines: 3)[" in typst("# Q\n\n::: div {.solution lines=3}\nA.\n:::\n")


def test_a_solution_without_attributes_reserves_nothing() -> None:
    body = typst("# Q\n\n::: solution\nAnswer.\n:::\n")

    assert "#exam-solution()[" in body


def test_lines_fill_asks_for_the_rest_of_the_page() -> None:
    assert '#exam-solution(lines: "fill")[' in typst("# Q\n\n::: solution {lines=fill}\nA.\n:::\n")


def test_a_box_reserves_a_framed_area() -> None:
    assert "#exam-solution(area: (auto, 3cm))[" in typst("# Q\n\n::: solution {box=3cm}\nA.\n:::\n")


def test_a_two_dimensional_box_keeps_both_dimensions() -> None:
    body = typst("# Q\n\n::: solution {box=6cmx4cm}\nA.\n:::\n")

    assert "#exam-solution(area: (6cm, 4cm))[" in body


def test_a_grid_reserves_squared_paper() -> None:
    assert "#exam-solution(grid: 6)[" in typst("# Q\n\n::: solution {grid=6}\nA.\n:::\n")


def test_an_empty_solution_only_reserves_space() -> None:
    body = typst("# Q\n\nText.\n\n::: solution {lines=fill newpage=true}\n:::\n")

    assert '#pagebreak(weak: true)\n\n#exam-reserve(lines: "fill")' in body
    assert "#exam-solution" not in body


def test_an_empty_solution_without_attributes_reserves_nothing() -> None:
    body = typst("# Q\n\nText.\n\n::: solution\n:::\n")

    assert "#exam-reserve" not in body


def test_compact_mode_asks_for_no_space_at_all() -> None:
    body = typst("# Q\n\n::: solution {lines=3}\nA.\n:::\n", compact=True)

    assert "#exam-solution()[" in body


def test_a_code_block_inside_a_solution_stays_ir() -> None:
    document = run_pass("# Q\n\n::: solution {lines=3}\n\n```c\nint x;\n```\n:::\n", backend="typst")

    assert any(isinstance(node, model.CodeBlock) for node in walk(document.ir))


# -- the rest of the document is left to the writer ------------------------


def test_a_thematic_break_is_left_to_the_writer() -> None:
    assert "#ts-divider()" in typst("# Q\n\nText.\n\n---\n\nMore.\n")


def test_a_callout_is_left_to_the_writer() -> None:
    assert "#ts-callout(" in typst("# Q\n\n!!! note\n    Careful.\n")


def test_a_raw_latex_block_is_dropped_by_the_typst_writer() -> None:
    # That is how one pass serves two backends: the emitters name their own
    # raw format and the other writer drops it.
    assert "clearpage" not in typst("# Q\n\n/// latex\n\\clearpage\n///\n")


# -- every call the emitter makes is one the scaffolding defines -----------


def test_the_scaffolding_defines_every_function_the_emitter_calls() -> None:
    snippets = (
        "# Q { points=5 newpage=true answer=x }\n\nT.\n",
        "# Q\n\n## - { points=1 }\n\nT.\n\n### -\n\nS.\n\n#### -\n\nSS.\n",
        "# Q\n\n## -\n\n- [x] A\n- [ ] B\n",
        "# Q\n\nA [x]{w=3cm} b.\n",
        "# Q\n\n::: solution {lines=3}\nA.\n:::\n\n::: solution {grid=4}\n:::\n",
        "# Q\n\n::: solution {box=2cm}\nA.\n:::\n",
    )
    called = set()
    for snippet in snippets:
        for mode in ({}, {"solution": True}):
            called.update(re.findall(r"#(exam-[a-z-]+)\(", typst(snippet, **mode)))

    scaffolding = TEMPLATE.read_text(encoding="utf-8")
    assert called
    for name in sorted(called):
        assert f"#let {name}(" in scaffolding, name

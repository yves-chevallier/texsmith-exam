"""The ``exam`` IR pass: parse a snippet, run the pass, read the LaTeX back."""

from __future__ import annotations

from conftest import latex, run_pass
from tmark.ir import model
from tmark.ir.walk import walk


# -- questions, parts, subparts -------------------------------------------


def test_a_top_level_heading_opens_a_titled_question() -> None:
    body = latex("# Syntaxe { points=10 }\n\nConsiderez.\n")

    assert r"\ExamQuestionsBegin" in body
    assert r"\titledquestion{Syntaxe}[10]\label{syntaxe}" in body


def test_a_dash_heading_is_an_anonymous_part_inside_parts() -> None:
    body = latex("# Q\n\n## -\n\nFirst.\n\n## -\n\nSecond.\n")

    assert body.count(r"\begin{parts}") == 1
    assert body.count("\n\\part\n") == 2
    assert body.rstrip().endswith(r"\end{parts}")
    assert r"\label" not in body.split(r"\begin{parts}")[1]


def test_a_question_before_a_figure_starts_its_own_paragraph() -> None:
    # exam.cls holds the `Problème N` label until the next horizontal material;
    # with a figure next it would be typeset above some later paragraph.
    body = latex("# Q { points=5 }\n\n![x](a.png)\n\nText.\n")

    assert r"\titledquestion{Q}[5]\label{q}\leavevmode" in body


def test_a_question_before_a_paragraph_keeps_its_pending_label() -> None:
    body = latex("# Q { points=5 }\n\nText.\n")

    assert r"\leavevmode" not in body
    assert r"\titledquestion{Q}[5]\label{q}" + "\nText." in body


def test_a_part_before_a_listing_keeps_its_pending_label() -> None:
    # The template's ``tscode`` hook reads ``\if@inlabel`` to hug a part label;
    # only a question needs its paragraph started on the spot.
    body = latex("# Q\n\n## -\n\n```c\nint x;\n```\n")

    assert r"\leavevmode" not in body


def test_a_part_opens_in_the_question_s_own_block() -> None:
    # A question heading followed straight by its first part: the two labels
    # are one block, so no \par separates them. With one, exam.cls hangs the
    # ``(a)`` on the ``Problème N`` title line.
    body = latex("# Q { points=10 }\n\n## -\n\nText.\n")

    assert "\\label{q}\n\\ExamQuestionsBegin\n\\begin{parts}" in body
    assert "\\label{q}\n\n" not in body


def test_a_subpart_opens_in_the_part_s_own_block() -> None:
    body = latex("# Q\n\n## -\n\n### -\n\nDeep.\n")

    assert "\\part\n\\ExamQuestionsBegin\n\\begin{subparts}" in body


def test_an_intro_paragraph_still_closes_the_question_label() -> None:
    # Nothing is carried when the question has text of its own to be glued to.
    body = latex("# Q\n\nIntro.\n\n## -\n\nText.\n")

    assert "\\label{q}\nIntro.\n\n\\ExamQuestionsBegin" in body


def test_points_reach_the_part() -> None:
    assert r"\part[3]" in latex("# Q\n\n## - { points=3 }\n\nText.\n")


def test_points_are_dropped_when_points_are_disabled() -> None:
    body = latex("# Q { points=10 }\n\n## - { points=3 }\n\nText.\n", points=False)

    assert r"\titledquestion{Q}\label{q}" in body
    assert "\n\\part\n" in body
    assert "[3]" not in body


def test_a_third_level_heading_opens_subparts_and_closes_them() -> None:
    body = latex("# Q\n\n## -\n\nPart.\n\n### -\n\nSub.\n\n## -\n\nNext.\n")

    assert r"\begin{subparts}" in body
    assert r"\subpart" in body
    assert body.index(r"\end{subparts}") < body.index(r"\part" + "\nNext.")
    assert body.rstrip().endswith(r"\end{parts}")


def test_a_heading_attribute_leaves_the_question_machinery() -> None:
    body = latex("# Q\n\n## Annexe { heading=true }\n\nText.\n")

    assert r"\ExamQuestionsEnd" in body
    assert r"\subsection{Annexe}" in body


def test_newpage_starts_the_question_on_a_fresh_page() -> None:
    body = latex("# Fonctions { points=15 newpage=true }\n\nText.\n")

    assert body.startswith("\\clearpage\n\\ExamQuestionsBegin")


def test_the_shallowest_heading_of_a_document_is_the_question_level() -> None:
    # A fragment that starts at level 2 numbers its questions all the same.
    body = latex("## Fonctions { points=4 }\n\nText.\n\n### -\n\nPart.\n")

    assert r"\titledquestion{Fonctions}[4]" in body
    assert r"\begin{parts}" in body


def test_an_answer_attribute_prints_an_answer_line_after_the_text() -> None:
    body = latex("# Q\n\n## - { points=1 answer=42 }\n\nWhat is it?\n")

    assert body.index("What is it?") < body.index(r"\answerline[42]")
    assert r"\ifprintanswers\answerline[42]\else\answerline\fi" in body


def test_a_named_question_keeps_its_answer_line_under_the_label() -> None:
    body = latex("# Q\n\n## `printf(\"%d\")` { points=1 answer=20 }\n\nText.\n")

    assert '\\part[1] \\tscodeinline{printf("\\%d")}\\label{printf-d}' in body
    assert body.index(r"\answerline[20]") < body.index("Text.")


def test_a_quoted_answer_survives_a_code_heading() -> None:
    # Regression, carried from the Python-Markdown reader: the smart-quote
    # inline pass rewrote ``"20"`` into a <q> element before attr_list could
    # read the block, and points/answer vanished. TMark parses the attribute
    # block itself, so the quotes never reach an inline pass.
    body = latex('# Q\n\n## `printf("%d ", a[1])` { points=1 answer="20" }\n\nText.\n')

    assert r"\answerline[20]" in body
    assert "{ points" not in body


def test_an_answer_value_may_hold_an_apostrophe() -> None:
    body = latex("# Q\n\n## - { points=1 answer=\"l\'index\" }\n\nText.\n")

    assert r"\answerline[l'index]" in body


# -- multiple choice -------------------------------------------------------


def test_a_task_list_becomes_a_choices_block_with_the_correct_letters() -> None:
    body = latex("# Q\n\n## -\n\n- [ ] Wrong\n- [x] Right\n- [ ] Other\n- [x] Also\n")

    assert r"\begin{samepage}" in body
    assert r"\begin{columen}[5]" in body
    assert r"\choice Wrong" in body
    assert r"\CorrectChoice Right" in body
    assert r"\ifprintanswers\answerline[B, D]\else\answerline\fi" in body
    assert body.rstrip().endswith(r"\end{parts}")


def test_a_task_list_without_a_correct_choice_prints_a_bare_answer_line() -> None:
    body = latex("# Q\n\n## -\n\n- [ ] One\n- [ ] Two\n")

    assert "\\answerline\n" in body
    assert r"\answerline[" not in body


def test_a_checkbox_style_uses_the_checkboxes_environment() -> None:
    body = latex("# Q\n\n## -\n\n- [x] Yes\n", style={"choices": "checkbox"})

    assert r"\begin{checkboxes}" in body


def test_compact_mode_drops_the_answer_line() -> None:
    body = latex("# Q\n\n## -\n\n- [x] Yes\n- [ ] No\n", compact=True)

    assert r"\answerline" not in body


def test_a_plain_bullet_list_is_not_a_choices_block() -> None:
    body = latex("# Q\n\n## -\n\n- One\n- Two\n")

    assert r"\begin{choices}" not in body
    assert r"\begin{itemize}" in body


def test_a_choice_body_keeps_its_inline_code_as_ir() -> None:
    # The body stays IR, so ``ts-code`` is still named in ``Requires``.
    document = run_pass("# Q\n\n## -\n\n- [x] `std::map`\n")

    assert any(isinstance(node, model.Code) for node in walk(document.ir))


# -- fill-in blanks --------------------------------------------------------


def test_a_span_with_a_width_becomes_a_fillin() -> None:
    body = latex("# Q\n\nLe mot [virtual]{w=3cm} ici.\n")

    assert r"\fillin[virtual][3cm]" in body


def test_a_bare_width_is_read_as_millimetres() -> None:
    assert r"\fillin[x][30mm]" in latex("# Q\n\nA [x]{w=30} b.\n")


def test_a_fillin_without_a_width_is_sized_from_the_answer() -> None:
    # 5 visible characters at 2.5 mm each.
    assert r"\fillin[abcde][12.5mm]" in latex("# Q\n\nA [abcde]{.fillin} b.\n")


def test_solution_mode_prints_the_answer_and_reserves_nothing() -> None:
    body = latex("# Q\n\nLe mot [virtual]{w=3cm} ici.\n", solution=True)

    assert r"\fillin[virtual]" in body
    assert "3cm" not in body


def test_a_bare_bracket_is_a_fillin_too() -> None:
    assert r"\fillin[path][10mm]" in latex("# Q\n\nThe [path] of it.\n")


def test_bare_fillins_can_be_turned_off() -> None:
    body = latex("# Q\n\nThe [path] of it.\n", fillin_bare=False)

    assert r"\fillin" not in body
    assert "[path]" in body


def test_brackets_inside_an_explicit_blank_stay_literal() -> None:
    # ``[\[D\]]{w=6cm}``: the answer *is* a bracketed pair, not a nested blank.
    body = latex("# Q\n\nA [B puis \\[BROWN\\]]{w=6cm} b.\n")

    assert body.count(r"\fillin") == 1
    assert r"\fillin[B puis [BROWN]][6cm]" in body


def test_a_link_is_never_a_fillin() -> None:
    body = latex("# Q\n\nSee [the docs](https://example.org).\n")

    assert r"\fillin" not in body
    assert r"\href{https://example.org}{the docs}" in body


# -- solution blocks -------------------------------------------------------


def test_a_solution_with_lines_reserves_dotted_lines() -> None:
    body = latex("# Q\n\n::: solution {lines=3}\nAnswer.\n:::\n")

    assert r"\begin{solutionordottedlines}[3\dottedlinefillheight]" in body
    assert "Answer." in body
    assert r"\leavevmode" in body
    assert r"\end{solutionordottedlines}" in body


def test_the_div_spelling_is_read_the_same_way() -> None:
    body = latex("# Q\n\n::: div {.solution lines=3}\nAnswer.\n:::\n")

    assert r"\begin{solutionordottedlines}[3\dottedlinefillheight]" in body


def test_a_declared_solution_admonition_is_read_the_same_way() -> None:
    body = latex(
        "---\npress:\n  declare:\n    admonitions:\n      solution:\n        title: Solution\n---\n"
        "\n# Q\n\n::: solution {lines=3}\nAnswer.\n:::\n"
    )

    assert r"\begin{solutionordottedlines}[3\dottedlinefillheight]" in body


def test_a_solution_without_attributes_only_shows_in_solution_mode() -> None:
    body = latex("# Q\n\n::: solution\nAnswer.\n:::\n")

    assert body.count(r"\ifprintanswers") == 1
    assert r"\begin{solution}" in body
    assert body.rstrip().endswith(r"\fi")


def test_lines_fill_fills_the_page_in_exam_mode() -> None:
    body = latex("# Q\n\n::: solution {lines=fill}\nAnswer.\n:::\n")

    assert r"\fillwithdottedlines{\stretch{1}}" in body


def test_a_line_style_switches_the_environment() -> None:
    body = latex("# Q\n\n::: solution {lines=3}\nA.\n:::\n", style={"text": "lines"})

    assert r"\begin{solutionorlines}[3\linefillheight]" in body


def test_a_box_reserves_a_framed_area() -> None:
    body = latex("# Q\n\n::: solution {box=3cm}\nA.\n:::\n")

    assert r"\begin{solutionorbox}[3cm]" in body


def test_a_grid_reserves_squared_paper() -> None:
    body = latex("# Q\n\n::: solution {grid=6}\nA.\n:::\n")

    assert r"\begin{solutionorgrid}[6\linefillheight]" in body


def test_a_box_with_two_dimensions_reserves_a_rectangle() -> None:
    body = latex("# Q\n\n::: solution {box=8cmx4cm}\nA.\n:::\n")

    assert r"\fbox{\parbox[c][4cm][c]{8cm}" in body


def test_a_table_in_a_solution_is_still_a_table() -> None:
    # Regression, carried from the Python-Markdown renderer: unwrapping the
    # solution wrapper used to re-parent the table out of the visitor's child
    # list, and the answer key printed the cells as running text. The body
    # stays IR here, so the table reaches the backend as one.
    body = latex("# Q\n\n::: solution\n| a | b |\n| --- | --- |\n| 1 | 2 |\n:::\n")

    assert r"\begin{tabularx}" in body
    assert r"\end{tabularx}" in body


def test_an_empty_solution_only_reserves_space() -> None:
    body = latex("# Q\n\nText.\n\n::: solution {lines=fill newpage=true}\n:::\n")

    assert r"\ifprintanswers\else" in body
    assert r"\clearpage" in body
    assert r"\fillwithdottedlines{\stretch{1}}" in body
    assert r"\begin{solution}" not in body


def test_an_empty_solution_without_attributes_reserves_nothing() -> None:
    # "the answer goes on a separate sheet": no space to reserve, nothing to print.
    body = latex("# Q\n\nText.\n\n::: solution\n:::\n")

    assert r"\fillwithdottedlines" not in body
    assert r"\ifprintanswers" in body
    assert r"\begin{solution}" in body


def test_solution_mode_surrounds_the_answer_with_skips() -> None:
    body = latex("# Q\n\n::: solution {lines=3}\nAnswer.\n:::\n", solution=True)

    assert r"\par\smallskip" in body


def test_a_code_block_inside_a_solution_stays_ir() -> None:
    # It must, or the ``highlight`` post-pass would never see it.
    document = run_pass("# Q\n\n::: solution {lines=3}\n\n```c\nint x;\n```\n:::\n")

    assert any(isinstance(node, model.CodeBlock) for node in walk(document.ir))


# -- the rest of the document is left alone --------------------------------


def test_a_thematic_break_is_left_to_the_writer() -> None:
    body = latex("# Q\n\nText.\n\n---\n\nMore.\n")

    assert r"\tsdivider" in body


def test_a_raw_latex_block_passes_through() -> None:
    body = latex("# Q\n\n/// latex\n\\clearpage\n///\n")

    assert r"\clearpage" in body


def test_a_callout_is_left_to_the_writer() -> None:
    body = latex("# Q\n\n!!! note\n    Careful.\n")

    assert r"\begin{tscallout}" in body


def test_a_document_without_headings_is_returned_unchanged() -> None:
    document = run_pass("Just a paragraph.\n")

    assert all(not isinstance(node, model.RawBlock) for node in walk(document.ir))

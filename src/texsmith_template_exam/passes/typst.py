"""The Typst emitters of the exam constructs (``template.typ`` markup).

The twin of :mod:`texsmith_template_exam.passes.latex`: one method per construct
of :mod:`texsmith_template_exam.passes.model`, the same descriptions in, Typst
markup out. Where the LaTeX emitter names the environments and macros of
``exam.cls``, this one names ``#exam-…`` functions the template's ``template.typ``
defines — so the body a document writes out stays as short and as readable as
the LaTeX one, and everything that decides how a question *looks* lives in the
scaffolding rather than in Python.

Two differences with the LaTeX side are structural, not cosmetic:

* **No list environments.** ``exam.cls`` numbers and indents through
  ``questions``/``parts``/``subparts``; Typst counters do the numbering, and the
  indentation is dropped because a page break — which a ``---`` and a
  ``newpage=true`` both are — is refused inside a Typst container
  (``pagebreaks are not allowed inside of containers``), and any indentation
  worth the name is one. So ``close_levels`` and ``plain_heading`` have nothing
  to emit, and the part label runs into the text the way it does in LaTeX.
* **Content blocks, not delimiters.** ``\\choice`` introduces a choice that runs
  to the next one; a Typst function takes its body in brackets. The multiple
  choice list is therefore emitted as a Typst bullet list inside one
  ``#exam-choices(...)[…]`` call, and ``exam-choices`` reads the items off the
  list it is handed — which is also what lets it letter them, lay them out in
  columns and mark the correct ones.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from texsmith_template_exam.exam.utils import auto_fillin_width, parse_box
from texsmith_template_exam.passes.model import Choice, ChoiceGroup, FillIn, Question, Solution
from texsmith_template_exam.passes.options import ExamOptions


#: The Typst function opening each exam depth (1-based), defined in template.typ.
_HEADING_FUNCTIONS = ("exam-question", "exam-part", "exam-subpart", "exam-subsubpart")
#: A length Typst parses as it stands.
_LENGTH = re.compile(r"\d+(?:\.\d+)?(?:mm|cm|in|pt|em)")


def typst_string(value: str) -> str:
    """``value`` as a Typst string literal (only ``\\`` and ``"`` need escaping there)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _length(value: str | None) -> str | None:
    """``value`` as a Typst length literal, ``None`` when it is not one."""
    if not value:
        return None
    candidate = value.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", candidate):
        return f"{candidate}mm"
    return candidate if _LENGTH.fullmatch(candidate) else None


def _measure(value: str | None) -> str | None:
    """A ``lines=`` / ``grid=`` value as the integer or the length Typst receives.

    A count of lines is an integer, and the scaffolding turns it into a height;
    an explicit dimension goes through as a length. ``fill`` is the caller's.
    """
    if value is None:
        return None
    candidate = value.strip()
    if candidate.isdigit():
        return candidate
    return _length(candidate)


def _call(name: str, arguments: dict[str, str]) -> str:
    """``#name(key: value, …)`` with the empty arguments dropped."""
    given = ", ".join(f"{key}: {value}" for key, value in arguments.items() if value)
    return f"#{name}({given})"


@dataclass(frozen=True, slots=True)
class TypstEmitter:
    """Turn exam constructs into the ``#exam-…`` calls ``template.typ`` defines."""

    options: ExamOptions
    raw_format: str = "typst"
    #: What separates the lines the pass assembles from these pieces.
    separator: str = "\n"

    # -- questions, parts, subparts ---------------------------------------

    def close_levels(self, closed: tuple[str, ...]) -> str:
        """Nothing: a Typst level is a counter, and counters need no closing."""
        return ""

    def plain_heading(self, closed: tuple[str, ...]) -> str:
        """Nothing: an ordinary heading is an ordinary ``=`` heading."""
        return ""

    def detached(self, question: Question) -> str:
        """Nothing: Typst typesets a question header where it stands."""
        return ""

    def question(
        self, question: Question, opened: tuple[str, ...], closed: tuple[str, ...]
    ) -> tuple[str, str]:
        """The call around a question's title inlines."""
        name = _HEADING_FUNCTIONS[min(question.depth, len(_HEADING_FUNCTIONS)) - 1]
        arguments = {
            "points": typst_string(question.points) if question.points else "",
            "id": typst_string(question.ref) if question.ref else "",
        }
        opening = f"{_call(name, arguments)}["
        if question.newpage:
            # A block, not an inline: the break has to end the paragraph the
            # raw inline sits in, or Typst refuses it inside one.
            opening = f"#pagebreak(weak: true)\n\n{opening}"
        return opening, "]"

    def answerline_frame(self) -> tuple[str, str]:
        """The call around the expected answer of an answer line."""
        return "#exam-answerline(answer: [", "])"

    def answerline(self, answer: str | None) -> str:
        """A whole answer line whose expected answer is markup already, or absent."""
        if not answer:
            return "#exam-answerline()"
        head, tail = self.answerline_frame()
        return f"{head}{answer}{tail}"

    # -- multiple choice ---------------------------------------------------

    def choices_frame(self, group: ChoiceGroup) -> tuple[str, str]:
        """The call around a whole multiple-choice list.

        The choices reach ``exam-choices`` as a Typst bullet list — one item per
        choice, written by :meth:`choice_marker` — because that is the one shape
        a marker with no closing delimiter can produce. The function reads the
        items off it, letters them, lays them out in columns and, in solution
        mode, emphasises the ones ``correct`` names. The letter style and the
        answer line are the document's, so the scaffolding reads them from the
        template attributes rather than from every call.
        """
        correct = "(" + "".join(f"{index}, " for index in group.correct_indices) + ")"
        return f"{_call('exam-choices', {'correct': correct})}[", "]"

    def choice_marker(self, choice: Choice) -> str:
        """A bullet: which choices are correct is the group's business, not the item's."""
        return "-"

    # -- fill-in blanks ----------------------------------------------------

    def fillin(self, blank: FillIn) -> tuple[str, str]:
        """The call around a blank's answer inlines."""
        if self.options.solution:
            return "#exam-fillin()[", "]"
        width = blank.width or auto_fillin_width(
            blank.plain, blank.scale or self.options.fillin_scale
        )
        return f"#exam-fillin(width: {_length(width) or '20mm'})[", "]"

    # -- solution blocks ---------------------------------------------------

    def solution(self, solution: Solution) -> tuple[str, str]:
        """The ``(open, close)`` markup around a solution body."""
        arguments = self._reservation(solution)
        if solution.empty and solution.reserves_space:
            # No answer to print: the block is the space and nothing else.
            reserve = _call("exam-reserve", arguments)
            if solution.newpage:
                reserve = f"#pagebreak(weak: true)\n\n{reserve}"
            return f"{reserve}\n", ""
        opening = f"{_call('exam-solution', arguments)}[\n"
        if solution.newpage and not self.options.solution:
            opening = f"#pagebreak(weak: true)\n\n{opening}"
        return opening, "\n]\n"

    def _reservation(self, solution: Solution) -> dict[str, str]:
        """What the scaffolding needs to reserve the space this block asks for."""
        if self.options.compact and not self.options.solution:
            return {}
        area = parse_box(solution.box) if solution.box else None
        if area is not None:
            width, height = area
            return {"area": f"({_length(width) or 'auto'}, {_length(height) or 'auto'})"}
        if solution.grid:
            return {"grid": _measure(solution.grid) or "0"}
        lines = (solution.lines or "").strip()
        if not lines:
            return {}
        if lines.lower() == "fill":
            return {"lines": typst_string("fill")}
        return {"lines": _measure(lines) or "0"}


__all__ = ["TypstEmitter", "typst_string"]

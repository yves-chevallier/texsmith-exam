"""The LaTeX emitters of the exam constructs (``exam.cls`` markup).

One method per construct of :mod:`texsmith_template_exam.passes.model`; the
pass hands over a description and gets markup back. This is the deliberate
narrow exception to "a pass rewrites nodes, never strings" that the bundled
``highlight`` pass also takes: ``exam.cls`` numbers its questions through
environments (``questions``/``parts``/``subparts``) that no container maps
onto, so the structure is emitted as raw blocks.

The markup a method returns **frames** content rather than replacing it: a
question title, a choice body, a fill-in answer stay IR nodes between an
opening and a closing raw string. That is not cosmetic — a construct inside
them (inline code, a highlight, an acronym) still reaches ``tmark.write``, so
it still names its fragment in ``Requires`` and the template still loads the
package that defines its contract macro.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from texsmith_template_exam.exam.utils import choice_label, expand_lines_value, normalize_box_dim
from texsmith_template_exam.passes.model import Choice, ChoiceGroup, FillIn, Question, Solution
from texsmith_template_exam.passes.options import ExamOptions


#: exam.cls list environments, outermost first.
LEVEL_ENVIRONMENTS: tuple[str, ...] = ("parts", "subparts", "subsubparts")
#: The heading command of each exam depth (1-based).
_HEADING_COMMANDS = ("question", "part", "subpart", "subsubpart")


def _parse_box(value: str) -> tuple[str, str] | None:
    """``box=`` as ``(width, height)``; the height is empty for a bare width."""
    raw = value.strip()
    if not raw:
        return None
    if "x" in raw:
        width_raw, height_raw = raw.split("x", 1)
        width = normalize_box_dim(width_raw)
        height = normalize_box_dim(height_raw)
        return (width, height) if (width and height) else None
    return (normalize_box_dim(raw), "")


def _auto_width(plain: str, scale: float) -> str:
    """The width reserved for an answer of ``plain``'s length."""
    visible = re.sub(r"\s+", "", plain or "")
    width_mm = max(1, len(visible)) * scale
    if float(width_mm).is_integer():
        return f"{int(width_mm)}mm"
    return f"{width_mm:.2f}".rstrip("0").rstrip(".") + "mm"


@dataclass(frozen=True, slots=True)
class LatexEmitter:
    """Turn exam constructs into ``exam.cls`` markup."""

    options: ExamOptions
    raw_format: str = "latex"
    #: What separates the lines the pass assembles from these pieces.
    separator: str = "\n"

    # -- questions, parts, subparts ---------------------------------------

    def close_levels(self, closed: tuple[str, ...]) -> str:
        return "\n".join(f"\\end{{{name}}}" for name in closed)

    def plain_heading(self, closed: tuple[str, ...]) -> str:
        lines = [f"\\end{{{name}}}" for name in closed]
        lines.append(r"\ExamQuestionsEnd")
        return "\n".join(lines)

    def question(
        self, question: Question, opened: tuple[str, ...], closed: tuple[str, ...]
    ) -> tuple[str, str]:
        """The markup around a question's title inlines."""
        lines = [r"\clearpage"] if question.newpage else []
        lines.append(r"\ExamQuestionsBegin")
        lines.extend(f"\\end{{{name}}}" for name in closed)
        lines.extend(f"\\begin{{{name}}}" for name in opened)
        head, tail = self._heading(question)
        lines.append(head)
        return "\n".join(lines), tail

    def _heading(self, question: Question) -> tuple[str, str]:
        command = _HEADING_COMMANDS[min(question.depth, len(_HEADING_COMMANDS)) - 1]
        points = f"[{question.points}]" if question.points else ""
        label = f"\\label{{{question.ref}}}" if question.ref else ""
        if question.depth == 1:
            if question.anonymous:
                return rf"\{command}{points}{label}", ""
            return r"\titledquestion{", rf"}}{points}{label}"
        if question.anonymous:
            return rf"\{command}{points}{label}", ""
        return rf"\{command}{points} ", label

    def detached(self, question: Question) -> str:
        r"""``\leavevmode`` when a question's title has no paragraph to open.

        ``\question`` and ``\titledquestion`` are list items, and ``\qformat``
        is their label: LaTeX holds a pending label until the next horizontal
        material, so a question followed by a figure — or by a listing, a table,
        a list — has its ``Problème N`` line typeset not above that block but
        above whichever later paragraph happens to start one. ``\leavevmode``
        starts the paragraph on the spot. Parts keep the pending label: the
        template's ``tscode`` hook reads ``\if@inlabel`` to hug them.
        """
        return r"\leavevmode" if question.depth == 1 else ""

    def answerline_frame(self) -> tuple[str, str]:
        """The markup around the expected answer of an answer line."""
        return r"\ifprintanswers\answerline[", r"]\else\answerline\fi"

    def answerline(self, answer: str | None) -> str:
        """A whole answer line whose expected answer is already markup (or absent)."""
        if not answer:
            return r"\answerline"
        head, tail = self.answerline_frame()
        return f"{head}{answer}{tail}"

    # -- multiple choice ---------------------------------------------------

    def choices_frame(self, group: ChoiceGroup) -> tuple[str, str]:
        env = "checkboxes" if self.options.choice_style == "checkbox" else "choices"
        head = "\n".join(
            (r"\begin{samepage}", r"\begin{columen}[5]", rf"\begin{{{env}}}")
        )
        tail = [rf"\end{{{env}}}", r"\end{columen}"]
        if not self.options.compact:
            labels = [choice_label(index) for index in group.correct_indices]
            tail.append(self.answerline(", ".join(labels) if labels else None))
        tail.append(r"\end{samepage}")
        return head, "\n".join(tail)

    def choice_marker(self, choice: Choice) -> str:
        return r"\CorrectChoice" if choice.correct else r"\choice"

    # -- fill-in blanks ----------------------------------------------------

    def fillin(self, blank: FillIn) -> tuple[str, str]:
        """The markup around a blank's answer inlines."""
        if self.options.solution:
            return "\\fillin[", "]"
        width = blank.width or _auto_width(blank.plain, blank.scale or self.options.fillin_scale)
        return "\\fillin[", f"][{width}]"

    # -- solution blocks ---------------------------------------------------

    def solution(self, solution: Solution) -> tuple[str, str]:
        """The ``(open, close)`` markup around a solution body."""
        if solution.empty and solution.reserves_space:
            return self._reserved_space(solution), ""
        begin, end = self._environment(solution)
        if self.options.solution:
            return "\\par\\smallskip\n" + begin, end + "\\par\\smallskip\n"
        return begin, end

    def _reserved_space(self, solution: Solution) -> str:
        """A solution block that is space and nothing else: no answer to print."""
        body = [r"\clearpage"] if solution.newpage else []
        body.append(self._filler(solution))
        return "\\ifprintanswers\\else\n" + "\n".join(body) + "\n\\fi\n"

    def _filler(self, solution: Solution) -> str:
        if solution.grid:
            grid = solution.grid.strip()
            if grid.isdigit():
                grid = f"{grid}\\linefillheight"
            return f"\\fillwithgrid{{{grid}}}"
        lines = (solution.lines or "fill").strip()
        if lines.lower() != "fill":
            height = expand_lines_value(lines, unit_macro=self._unit_macro())
            return f"{self._fill_command()}{{{height}}}"
        return f"{self._fill_command()}{{\\stretch{{1}}}}"

    def _unit_macro(self) -> str:
        if self.options.text_style in {"lines", "box"}:
            return "linefillheight"
        return "dottedlinefillheight"

    def _fill_command(self) -> str:
        return {
            "lines": r"\fillwithlines",
            "box": r"\makeemptybox",
        }.get(self.options.text_style, r"\fillwithdottedlines")

    def _environment(self, solution: Solution) -> tuple[str, str]:
        if self.options.compact and not self.options.solution:
            return (
                "\\ifprintanswers\n\\begin{solution}\n",
                "\\leavevmode\n\\end{solution}\n\\fi\n",
            )

        if solution.box:
            parsed = _parse_box(solution.box)
            if parsed:
                width, height = parsed
                if height:
                    centered = width == height
                    prefix = "\\noindent\\hfill" if centered else "\\noindent"
                    suffix = "\\hfill" if centered else ""
                    return (
                        "\\ifprintanswers\n\\begin{solution}\n",
                        "\\leavevmode\n\\end{solution}\n\\else\n"
                        "\\par\n\\penalty 0\n\\vspace{1em}%\n"
                        f"{prefix}\\fbox{{\\parbox[c][{height}][c]{{{width}}}"
                        f"{{\\rule{{0pt}}{{{height}}}}}}}{suffix}%\n"
                        "\\vspace{1em}%\n\\fi\n",
                    )
                if width:
                    return (
                        f"\\begin{{solutionorbox}}[{width}]\n",
                        "\\leavevmode\n\\end{solutionorbox}\n",
                    )

        if solution.grid:
            grid = solution.grid.strip()
            if grid.isdigit():
                grid = f"{grid}\\linefillheight"
            return (
                f"\\begin{{solutionorgrid}}[{grid}]\n",
                "\\leavevmode\n\\end{solutionorgrid}\n",
            )

        lines = (solution.lines or "").strip()
        if not lines:
            return (
                "\\ifprintanswers\n\\begin{solution}\n",
                "\\leavevmode\n\\end{solution}\n\\fi\n",
            )

        if lines.lower() == "fill":
            filler = f"{self._fill_command()}{{\\stretch{{1}}}}"
            newpage = "\\clearpage\n" if solution.newpage else ""
            return (
                "\\ifprintanswers\n\\begin{solution}\n",
                f"\\leavevmode\n\\end{{solution}}\n\\else\n{newpage}{filler}\n\\fi\n",
            )

        height = expand_lines_value(lines, unit_macro=self._unit_macro())
        environment = {
            "lines": "solutionorlines",
            "box": "solutionorbox",
        }.get(self.options.text_style, "solutionordottedlines")
        return (
            f"\\begin{{{environment}}}[{height}]\n",
            f"\\leavevmode\n\\end{{{environment}}}\n",
        )


__all__ = ["LEVEL_ENVIRONMENTS", "LatexEmitter"]

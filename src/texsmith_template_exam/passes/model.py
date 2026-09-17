"""Backend-neutral descriptions of the exam constructs.

:mod:`texsmith_template_exam.passes.exam` recognises the constructs in the IR
and describes them with the dataclasses below; a backend emitter
(:mod:`~texsmith_template_exam.passes.latex`, later a Typst twin) turns each
description into markup. Nothing here knows about LaTeX.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:  # pragma: no cover - typing only
    from tmark.ir import model as ir


@dataclass(frozen=True, slots=True)
class Question:
    """A heading that opens a question, a part, a subpart or a subsubpart.

    ``depth`` is the *exam* depth (1 = question, 2 = part, 3 = subpart,
    4 = subsubpart), already normalised against the shallowest heading of the
    document, the way the ``headings`` pass normalises ``base_level``.
    """

    depth: int
    #: The inline content of the heading, rendered by the emitter.
    title: tuple[ir.Inline, ...]
    #: A dash-only or empty title: the question carries no name.
    anonymous: bool
    #: ``points=…``; ``None`` when absent or when points are disabled.
    points: str | None = None
    #: The cross-reference label, ``None`` for an anonymous question.
    ref: str | None = None
    #: ``answer=…``: a short expected answer printed on an answer line.
    answer: str | None = None
    #: ``newpage=true``: the question starts on a fresh page.
    newpage: bool = False


@dataclass(frozen=True, slots=True)
class Choice:
    """One entry of a multiple-choice list."""

    correct: bool
    body: tuple[ir.Block, ...]


@dataclass(frozen=True, slots=True)
class ChoiceGroup:
    """A task list read as a multiple-choice question."""

    choices: tuple[Choice, ...]

    @property
    def correct_indices(self) -> tuple[int, ...]:
        return tuple(index for index, choice in enumerate(self.choices) if choice.correct)


@dataclass(frozen=True, slots=True)
class FillIn:
    """An inline blank: ``[answer]{w=3cm}``."""

    #: The inline content of the answer, rendered by the emitter.
    answer: tuple[ir.Inline, ...]
    #: The answer as plain text, used to size an auto-width blank.
    plain: str
    #: An explicit ``w=`` / ``width=`` value, already normalised (``30`` → ``30mm``).
    width: str | None = None
    #: A per-blank ``char-width-scale=`` override.
    scale: float | None = None


@dataclass(frozen=True, slots=True)
class Solution:
    """A ``::: solution`` container and the space it reserves in exam mode."""

    #: ``lines=N`` or ``lines=fill``.
    lines: str | None = None
    #: ``grid=N`` or ``grid=<dimension>``.
    grid: str | None = None
    #: ``box=<width>`` or ``box=<width>x<height>``.
    box: str | None = None
    #: ``newpage=true``: break the page before the reserved space (exam mode only).
    newpage: bool = False
    #: The blocks of the answer; empty means "reserve space, print nothing".
    content: tuple[ir.Block, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return not self.content

    @property
    def reserves_space(self) -> bool:
        """Whether the author asked for space: ``lines``, ``grid`` or ``box``.

        Without one of them there is nothing to reserve, so an empty block is
        an answer given elsewhere (on a separate sheet) rather than a blank to
        fill in — it prints nothing on either copy.
        """
        return bool(self.lines or self.grid or self.box)


class Emitter(Protocol):
    """What :mod:`~texsmith_template_exam.passes.exam` needs from a backend.

    Most methods return a ``(open, close)`` pair *framing* content that stays
    IR: the pass splices the pair around the nodes as raw inlines, so whatever
    the author wrote inside — inline code, a highlight, an acronym — still
    reaches the writer and still names the fragment that defines its contract
    macro. ``raw_format`` names the format of the raw nodes (``latex``,
    ``typst``); ``separator`` is what joins the assembled lines.
    """

    raw_format: str
    separator: str

    def question(
        self, question: Question, opened: tuple[str, ...], closed: tuple[str, ...]
    ) -> tuple[str, str]:
        """The markup around a question's title, levels to close and open included."""

    def detached(self, question: Question) -> str:
        """What closes a question's opening when no prose follows it to be glued to.

        A figure, a listing, a list, a table: the backend may need the title
        typeset where it stands rather than deferred to the next paragraph.
        """

    def close_levels(self, closed: tuple[str, ...]) -> str:
        """The markup closing the still-open levels at the end of a document."""

    def plain_heading(self, closed: tuple[str, ...]) -> str:
        """The markup leaving the question machinery before an ordinary heading."""

    def answerline_frame(self) -> tuple[str, str]:
        """The markup around the expected answer of an answer line."""

    def answerline(self, answer: str | None) -> str:
        """A whole answer line whose expected answer is markup already, or absent."""

    def choices_frame(self, group: ChoiceGroup) -> tuple[str, str]:
        """The markup around a whole multiple-choice list, answer line included."""

    def choice_marker(self, choice: Choice) -> str:
        """What introduces one choice."""

    def fillin(self, blank: FillIn) -> tuple[str, str]:
        """The markup around an inline blank's answer."""

    def solution(self, solution: Solution) -> tuple[str, str]:
        """The markup around a solution body."""


__all__ = [
    "Choice",
    "ChoiceGroup",
    "Emitter",
    "FillIn",
    "Question",
    "Solution",
]

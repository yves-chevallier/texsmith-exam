"""The exam options a pass reads from its :class:`~texsmith.passes.PassContext`.

Backend-neutral: the same options drive the LaTeX emitters and, later, the
Typst ones. Every flag is resolved through ``ctx.attribute(...)`` — the
template overrides (front matter merged with the CLI's ``-a key=value``) first,
then the front matter — so ``-a solution=true`` and ``exam: {solution: true}``
mean the same thing, as they did through ``exam.mode.resolve_value``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from texsmith_template_exam.exam.utils import normalize_style_choice


if TYPE_CHECKING:  # pragma: no cover - typing only
    from texsmith.passes import PassContext


#: The width, in millimetres, reserved per character of an auto-sized fill-in.
DEFAULT_FILLIN_SCALE = 2.5

_SOLUTION_KEYS = ("solution", "exam.solution", "press.solution")
_COMPACT_KEYS = ("compact", "exam.compact", "press.compact")
_POINTS_KEYS = ("points", "exam.points")
_STYLE_KEYS = ("style", "exam.style")
_BARE_FILLIN_KEYS = ("fillin-bare", "fillin_bare", "exam.fillin-bare", "exam.fillin_bare")
_SCALE_KEYS = (
    "char-width-scale",
    "fillin_char_width_scale",
    "style.char-width-scale",
    "fillin.char-width-scale",
    "exam.char-width-scale",
    "exam.fillin.char-width-scale",
)


def coerce_bool(value: Any, *, default: bool) -> bool:
    """``value`` as a boolean, ``default`` when it spells nothing recognisable."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def coerce_scale(value: Any, *, default: float) -> float:
    """A positive float, ``default`` otherwise."""
    try:
        scale = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return scale if scale > 0 else default


def first_attribute(ctx: PassContext, keys: tuple[str, ...]) -> Any:
    """The first of ``keys`` the context resolves to something that is not ``None``."""
    for key in keys:
        value = ctx.attribute(key)
        if value is not None:
            return value
    return None


@dataclass(frozen=True, slots=True)
class ExamOptions:
    """What the exam constructs need to know about the document being rendered."""

    #: ``-a solution=true`` / ``exam.solution``: answers are printed.
    solution: bool = False
    #: ``exam.compact``: no reserved answer space, no answer lines.
    compact: bool = False
    #: ``exam.points``: points are shown and the grade table is printed.
    points: bool = True
    #: ``exam.style.choices``: ``alpha`` (``choices``) or ``checkbox``.
    choice_style: str = "alpha"
    #: ``exam.style.text``: ``dotted``, ``lines`` or ``box``.
    text_style: str = "dotted"
    #: Millimetres per character of an auto-sized fill-in.
    fillin_scale: float = DEFAULT_FILLIN_SCALE
    #: ``exam.fillin-bare``: read a bare ``[answer]`` in prose as a blank.
    #: On, because that is the spelling the corpus and the demo were written
    #: in; ``[answer]{.fillin}`` says the same thing and always works.
    bare_fillin: bool = True

    @classmethod
    def from_context(cls, ctx: PassContext) -> ExamOptions:
        """Resolve the options of the document ``ctx`` describes."""
        style = first_attribute(ctx, _STYLE_KEYS)
        style_map = style if isinstance(style, dict) else {}
        scale = first_attribute(ctx, _SCALE_KEYS)
        return cls(
            solution=coerce_bool(first_attribute(ctx, _SOLUTION_KEYS), default=False),
            compact=coerce_bool(first_attribute(ctx, _COMPACT_KEYS), default=False),
            points=coerce_bool(first_attribute(ctx, _POINTS_KEYS), default=True),
            choice_style=normalize_style_choice(
                style_map.get("choices"),
                default="alpha",
                aliases={"checkboxes": "checkbox", "check": "checkbox"},
            ),
            text_style=normalize_style_choice(
                style_map.get("text"),
                default="dotted",
                aliases={"dots": "dotted", "dottedlines": "dotted", "line": "lines"},
            ),
            fillin_scale=coerce_scale(scale, default=DEFAULT_FILLIN_SCALE),
            bare_fillin=coerce_bool(first_attribute(ctx, _BARE_FILLIN_KEYS), default=True),
        )


__all__ = [
    "DEFAULT_FILLIN_SCALE",
    "ExamOptions",
    "coerce_bool",
    "coerce_scale",
    "first_attribute",
]

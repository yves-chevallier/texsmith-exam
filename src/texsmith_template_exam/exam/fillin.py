"""Shared helpers to build exam fill-in LaTeX."""

from __future__ import annotations

import re

from texsmith.core.context import RenderContext

from texsmith_template_exam.exam.mode import resolve_value
from texsmith_template_exam.exam.utils import normalize_fillin_width


_FILLIN_WIDTH_PATTERN = re.compile(r"\b(?:w|width)\s*=\s*([^\s,}]+)")
_FILLIN_SCALE_PATTERN = re.compile(r"\bchar-width-scale\s*=\s*([^\s,}]+)")


def extract_fillin_width(attrs: str) -> str:
    match = _FILLIN_WIDTH_PATTERN.search(attrs)
    if not match:
        return ""
    return match.group(1)


def extract_fillin_scale(attrs: str) -> str:
    match = _FILLIN_SCALE_PATTERN.search(attrs)
    if not match:
        return ""
    return match.group(1)


def coerce_fillin_scale(value: object, *, default: float) -> float:
    try:
        scale = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return scale if scale > 0 else default


def fillin_scale_from_context(context: RenderContext, *, default_scale: float = 2.5) -> float:
    for key in (
        "char-width-scale",
        "fillin_char_width_scale",
        "style.char-width-scale",
        "fillin.char-width-scale",
        "exam.char-width-scale",
        "exam.fillin.char-width-scale",
    ):
        value = resolve_value(context, (key,), include_runtime=True, include_front_matter=True)
        if value is not None:
            return coerce_fillin_scale(value, default=default_scale)
    return default_scale


def auto_fillin_width(answer_raw: str, scale: float) -> str:
    visible = re.sub(r"\s+", "", answer_raw or "")
    length = max(1, len(visible))
    width_mm = length * scale
    if width_mm.is_integer():
        width_value = f"{int(width_mm)}mm"
    else:
        width_value = f"{width_mm:.2f}".rstrip("0").rstrip(".") + "mm"
    return width_value


def compute_fillin_width(
    *,
    answer_raw: str,
    attrs: str,
    context: RenderContext,
    default_scale: float = 2.5,
) -> str:
    width_value = normalize_fillin_width(extract_fillin_width(attrs))
    if not width_value:
        scale_raw = extract_fillin_scale(attrs)
        scale = coerce_fillin_scale(
            scale_raw if scale_raw else fillin_scale_from_context(context, default_scale=default_scale),
            default=default_scale,
        )
        width_value = auto_fillin_width(answer_raw, scale)
    return width_value


def build_fillin_latex(
    *,
    answer_raw: str,
    answer_latex: str,
    attrs: str,
    context: RenderContext,
    solution_mode: bool,
    default_scale: float = 2.5,
) -> str:
    width_value = compute_fillin_width(
        answer_raw=answer_raw,
        attrs=attrs,
        context=context,
        default_scale=default_scale,
    )
    if solution_mode:
        return f"\\fillin[{answer_latex}]"
    return f"\\fillin[{answer_latex}][{width_value}]"


__all__ = [
    "auto_fillin_width",
    "build_fillin_latex",
    "coerce_fillin_scale",
    "compute_fillin_width",
    "extract_fillin_scale",
    "extract_fillin_width",
    "fillin_scale_from_context",
]

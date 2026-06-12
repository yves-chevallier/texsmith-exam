"""Resolution of exam rule presets/tokens into the cover-page rule list.

The exam template lets an exam reference rules by token instead of repeating the
full sentences. The built-in library lives in ``exam/rules.yml`` (consignes,
standards, presets). The ``exam.rules`` front-matter entry accepts:

* a list of tokens / literal sentences, e.g. ``[name, legible, ..., c17]``
* a mapping with ``preset`` and optional ``standard`` / ``prepend`` / ``append``::

      rules:
        preset: te
        standard: c17

This module registers an ``exam_rules`` attribute normaliser so TeXSmith expands
the reference into a plain list of strings when resolving the ``rules`` template
attribute — no project-side preprocessing required.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_LIBRARY_PATH = Path(__file__).resolve().parent / "exam" / "rules.yml"


@lru_cache(maxsize=1)
def _library() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (token -> sentence, preset -> token list) from the bundled library."""
    data = yaml.safe_load(_LIBRARY_PATH.read_text(encoding="utf-8")) or {}
    tokens: dict[str, str] = {}
    for section in ("consignes", "standards"):
        for key, value in (data.get(section) or {}).items():
            tokens[str(key)] = str(value)
    presets = {
        str(name): [str(tok) for tok in seq]
        for name, seq in (data.get("presets") or {}).items()
    }
    return tokens, presets


def _resolve_token(token: str, tokens: dict[str, str]) -> str:
    """A known token maps to its sentence; anything else is a literal sentence."""
    return tokens.get(token, token)


def resolve_rules(value: Any) -> list[str]:
    """Expand an ``exam.rules`` value into a flat list of sentences."""
    tokens, presets = _library()

    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if isinstance(value, list):
        return [_resolve_token(str(item), tokens) for item in value]

    if isinstance(value, dict):
        sequence: list[str] = [str(t) for t in value.get("prepend", []) or []]
        preset = value.get("preset")
        if preset is not None:
            if str(preset) not in presets:
                available = ", ".join(sorted(presets)) or "(none)"
                raise ValueError(
                    f"Unknown exam rules preset '{preset}'. Available presets: {available}."
                )
            sequence.extend(presets[str(preset)])
        standard = value.get("standard")
        if standard is not None:
            sequence.append(str(standard))
        sequence.extend(str(t) for t in value.get("append", []) or [])
        return [_resolve_token(tok, tokens) for tok in sequence]

    raise ValueError(f"Unsupported `exam.rules` value of type {type(value).__name__}.")


def resolve_attribute(value: Any, _spec: Any = None, fallback: Any = None) -> Any:
    """TeXSmith attribute normaliser for the ``rules`` cover-page attribute.

    Referenced from ``manifest.toml`` as
    ``normaliser = "texsmith_template_exam.rules:resolve_attribute"``. TeXSmith
    imports and calls it with ``(value, spec, fallback)`` after coercing the
    attribute value; it expands presets/tokens into the final list of sentences.
    """
    resolved = resolve_rules(value)
    if not resolved and fallback:
        return fallback
    return resolved

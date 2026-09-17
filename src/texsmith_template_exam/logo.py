"""Which HEIG-VD logo vintage a Typst exam draws.

The LaTeX side gets the logo from the ``heiglogo`` *fragment*, which picks the
vintage from the document date in Python and hands ``\\logo[year=…]`` the
answer. Fragments are LaTeX-only, so the Typst scaffolding needs the same
answer by another road: this module is a template-attribute normaliser
(``manifest.toml``, ``[typst.template.attributes.logo_vintage]``), and
``template.typ`` includes ``logos/heiglogo-<vintage>.typ`` — the SVG
``scripts/heiglogo-typst.py`` translated once from the package's TikZ paths.

The rule itself stays the fragment's: a vintage is in force from the year it
was introduced, and the document date says which year that is.
"""

from __future__ import annotations

from typing import Any


#: The vintages ``exam/template/logos/`` ships, oldest first.
VINTAGES: tuple[str, ...] = ("1998", "2004", "2009", "2020")
#: What a document with no usable date gets: the current letterhead.
LATEST_VINTAGE = VINTAGES[-1]


def resolve_vintage(date_value: Any) -> str:
    """The vintage in force at ``date_value``, the latest when it says nothing."""
    try:
        from texsmith_fragment_heig_logo._vintage import resolve_vintage as from_fragment
    except ImportError:
        # The fragment package is the owner of the rule; without it the Typst
        # build still draws a logo, the current one.
        return LATEST_VINTAGE
    resolved = from_fragment(None, date_value, default=LATEST_VINTAGE)
    return resolved if resolved in VINTAGES else LATEST_VINTAGE


def resolve_attribute(value: Any, _spec: Any = None, _fallback: Any = None) -> str:
    """TeXSmith attribute normaliser: a document ``date`` in, a vintage out."""
    return resolve_vintage(value)


__all__ = ["LATEST_VINTAGE", "VINTAGES", "resolve_attribute", "resolve_vintage"]

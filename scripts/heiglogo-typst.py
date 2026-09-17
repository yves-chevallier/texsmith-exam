#!/usr/bin/env python3
"""Regenerate the Typst logo library from the ``heiglogo`` LaTeX package.

The HEIG-VD logo has no image file: ``heiglogo.sty`` draws each vintage with
TikZ paths, and the LaTeX side of the exam template gets it from the
``heiglogo`` *fragment*, which is LaTeX-only. Typst needs a picture, so the
same paths are translated once — here — into SVG, and the SVG is inlined in
``exam/template/logos/heiglogo-<vintage>.typ`` as a Typst string the
scaffolding hands to ``#image(bytes(…), format: "svg")``.

Run it when the vendored ``heiglogo.sty`` changes; the output is committed, so
a build needs neither this script nor the fragment package::

    uv run python scripts/heiglogo-typst.py

The path syntax used by the package is small and closed: ``(x,y)`` opens a
subpath, ``--(x,y)`` draws a line, ``..controls(a,b)and(c,d)..(x,y)`` a cubic,
``--cycle`` closes, ``(x,y) rectangle (x,y)`` is a box. TikZ's y axis points
up and SVG's points down, so every ordinate is mirrored about the vintage's
own height.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


REPO = Path(__file__).resolve().parents[1]
DESTINATION = REPO / "src/texsmith_template_exam/exam/template/logos"

#: ``\fill[<key>]`` → the colour it means, monochrome first, then ``color=true``.
#: Mirrors the ``\ifheiglogo@iscolor`` branches of each ``heiglogo@draw@`` macro
#: and the palette defined at the top of the package.
PALETTE: dict[str, dict[str, tuple[str, str]]] = {
    "1998": {
        r"\heiglogo@c@a": ("#000000", "#00a651"),
        r"\heiglogo@c@b": ("#000000", "#ed1c29"),
        r"\heiglogo@c@c": ("#000000", "#231f20"),
    },
    "2004": {
        r"\heiglogo@logocolor": ("#000000", "#ee3124"),
        "white": ("#ffffff", "#ffffff"),
    },
    "2009": {
        r"\heiglogo@logocolor": ("#000000", "#a63136"),
    },
    "2020": {
        r"\heiglogo@curcolor": ("#000000", "#e1251b"),
        "white": ("#ffffff", "#ffffff"),
    },
}

_DRAW_RE = re.compile(r"\\expandafter\\def\\csname heiglogo@draw@(\d{4})\\endcsname\{")
_SETYEAR_RE = re.compile(
    r"\\expandafter\\def\\csname heiglogo@setyear@(\d{4})\\endcsname\{(.*?)\n\}", re.S
)
_FILL_RE = re.compile(r"\\fill\[([^\]]*)\]\s*(.*?);", re.S)
_TOKEN_RE = re.compile(
    r"""
    \(\s*(?P<x>-?[\d.]+)\s*,\s*(?P<y>-?[\d.]+)\s*\)   # a coordinate
  | \.\.controls\s*\(\s*(?P<ax>-?[\d.]+)\s*,\s*(?P<ay>-?[\d.]+)\s*\)
    \s*and\s*\(\s*(?P<bx>-?[\d.]+)\s*,\s*(?P<by>-?[\d.]+)\s*\)\s*\.\.
  | (?P<rect>rectangle)
  | (?P<cycle>cycle)
  | (?P<line>--)
    """,
    re.X,
)


def _package_source() -> Path:
    """The vendored ``heiglogo.sty`` of the installed fragment package."""
    try:
        from texsmith_fragment_heig_logo._fragment import FRAGMENT_PATH
    except ImportError:  # pragma: no cover - developer tooling
        sys.exit(
            "texsmith-fragment-heig-logo is not installed; it is where heiglogo.sty lives."
        )
    return Path(FRAGMENT_PATH) / "heiglogo.sty"


def _braced(text: str, start: int) -> tuple[str, int]:
    """The balanced ``{…}`` group opening at ``start - 1``, and what follows it."""
    depth, index = 1, start
    while depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    return text[start : index - 1], index


def geometry(source: str) -> dict[str, dict[str, str]]:
    """Each vintage's native box and default size, from its ``setyear`` macro."""
    out: dict[str, dict[str, str]] = {}
    for match in _SETYEAR_RE.finditer(source):
        body = match.group(2)
        keys = dict(re.findall(r"\\def\\heiglogo@(\w+)\{([^}]*)\}", body))
        out[match.group(1)] = keys
    return out


def drawings(source: str) -> dict[str, str]:
    """The body of each ``heiglogo@draw@<vintage>`` macro."""
    out: dict[str, str] = {}
    for match in _DRAW_RE.finditer(source):
        body, _ = _braced(source, match.end())
        out[match.group(1)] = body
    return out


def _number(value: float) -> str:
    return f"{value:g}"


def path_data(spec: str, height: float) -> str:
    """One TikZ path as an SVG ``d`` attribute, mirrored about ``height``."""
    tokens = list(_TOKEN_RE.finditer(spec))
    parts: list[str] = []
    index = 0

    def point(match: re.Match[str], prefix: str = "") -> tuple[str, str]:
        x = _number(float(match.group(f"{prefix}x")))
        y = _number(height - float(match.group(f"{prefix}y")))
        return x, y

    while index < len(tokens):
        token = tokens[index]
        if token.group("x") is not None:
            follows = tokens[index + 1] if index + 1 < len(tokens) else None
            if follows is not None and follows.group("rect"):
                corner = tokens[index + 2]
                x1, y1 = point(token)
                x2, y2 = point(corner)
                parts.append(f"M {x1} {y1} L {x2} {y1} L {x2} {y2} L {x1} {y2} Z")
                index += 3
                continue
            x, y = point(token)
            parts.append(f"M {x} {y}")
            index += 1
        elif token.group("line"):
            follows = tokens[index + 1]
            if follows.group("cycle"):
                parts.append("Z")
            else:
                x, y = point(follows)
                parts.append(f"L {x} {y}")
            index += 2
        elif token.group("ax") is not None:
            follows = tokens[index + 1]
            ax, ay = point(token, "a")
            bx, by = point(token, "b")
            x, y = point(follows)
            parts.append(f"C {ax} {ay} {bx} {by} {x} {y}")
            index += 2
        else:  # pragma: no cover - a bare `cycle` never starts a step
            index += 1
    return " ".join(parts)


def svg(vintage: str, body: str, box: dict[str, str], *, color: bool) -> str:
    """The whole vintage as one SVG document, quoted with ``'`` so a Typst string holds it."""
    width = float(box["nativewidth"])
    height = float(box["nativeheight"])
    palette = PALETTE[vintage]
    paths: list[str] = []
    for match in _FILL_RE.finditer(body):
        options = [item.strip() for item in match.group(1).split(",")]
        key = options[0]
        fill = palette[key][1 if color else 0]
        rule = " fill-rule='evenodd'" if "even odd rule" in match.group(1) else ""
        paths.append(f"<path d='{path_data(match.group(2), height)}' fill='{fill}'{rule}/>")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' "
        f"viewBox='0 0 {_number(width)} {_number(height)}'>"
        + "".join(paths)
        + "</svg>"
    )


def library(vintage: str, body: str, box: dict[str, str]) -> str:
    """The ``.typ`` file of one vintage: the two SVGs and the package's own default size."""
    mode = box.get("defsizemode", "height")
    size = box.get("defsize", "18mm")
    return "\n".join(
        (
            f"// HEIG-VD logo, vintage {vintage} — generated by scripts/heiglogo-typst.py",
            "// from the TikZ paths of heiglogo.sty. Do not edit: regenerate.",
            f'#let heig-logo-vintage = "{vintage}"',
            f'#let heig-logo-size = (mode: "{mode}", value: {size})',
            f'#let heig-logo-mono = "{svg(vintage, body, box, color=False)}"',
            f'#let heig-logo-color = "{svg(vintage, body, box, color=True)}"',
            "",
        )
    )


def main() -> None:
    source = _package_source().read_text(encoding="utf-8")
    boxes = geometry(source)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for vintage, body in drawings(source).items():
        target = DESTINATION / f"heiglogo-{vintage}.typ"
        target.write_text(library(vintage, body, boxes[vintage]), encoding="utf-8")
        print(f"wrote {target.relative_to(REPO)}")  # noqa: T201


if __name__ == "__main__":
    main()

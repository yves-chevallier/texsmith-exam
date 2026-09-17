"""Small, pure helpers shared across exam renderers."""

from __future__ import annotations

import re


_EMPTY_TITLE_PATTERN = re.compile(r"^[_\-\u2010\u2011\u2012\u2013\u2014\u2212]+$")
_HEADING_ATTR_PATTERN = re.compile(
    r'(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?P<value>"[^"]*"|\'[^\']*\'|«[^»]*»|“[^”]*”|[^,\s]+)'
)


def extract_dash_attrs_prefix(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    if not stripped.startswith("-"):
        return None
    cursor = stripped[1:].lstrip()
    if not cursor:
        return None

    open_idx = None
    if cursor.startswith("\\{"):
        open_idx = 1
    elif cursor.startswith("{"):
        open_idx = 0
    if open_idx is None:
        return None

    depth = 0
    end_idx = None
    for idx in range(open_idx, len(cursor)):
        ch = cursor[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = idx
                break
    if end_idx is None or depth != 0:
        return None

    attrs = cursor[open_idx + 1 : end_idx]
    tail = cursor[end_idx + 1 :].strip()
    return attrs, tail


def parse_heading_attrs(attrs: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for match in _HEADING_ATTR_PATTERN.finditer(attrs):
        key = match.group("key").strip().lower().replace("-", "_")
        value = match.group("value").strip()
        if len(value) >= 2 and (
            (value[0] == '"' and value[-1] == '"')
            or (value[0] == "'" and value[-1] == "'")
            or (value[0] == "«" and value[-1] == "»")
            or (value[0] == "“" and value[-1] == "”")
        ):
            value = value[1:-1]
        parsed[key] = value
    return parsed


def normalize_style_choice(value: object | None, *, default: str, aliases: dict[str, str]) -> str:
    if value is None:
        return default
    candidate = str(value).strip().lower()
    if not candidate:
        return default
    return (
        aliases.get(candidate, candidate)
        if candidate in aliases or candidate in aliases.values()
        else default
    )


def normalize_points(points: str | None) -> str | None:
    if points is None:
        return None
    trimmed = points.strip()
    return trimmed or None


def normalize_answer_text(answer: str | None) -> str | None:
    if answer is None:
        return None
    text = answer.strip()
    if len(text) >= 2:
        quote_pairs = {
            ("`", "`"),
            ('"', '"'),
            ("'", "'"),
            ("«", "»"),
            ("“", "”"),
        }
        if (text[0], text[-1]) in quote_pairs:
            text = text[1:-1].strip()
    return text or None


def normalize_fillin_width(value: str) -> str:
    normalized = value.strip().rstrip("\\")
    if not normalized:
        return normalized
    if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return f"{normalized}mm"
    return normalized


def normalize_box_dim(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return normalized
    if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return f"{normalized}mm"
    return normalized


def markdown_to(value: object | None, backend: str) -> str:
    """A line or two of Markdown as ``backend`` markup — tmark parses, tmark writes.

    A template attribute declared ``format = "markdown"`` goes through the same
    parser and writer; a cover-page rule is one item of a *list*, so the
    attribute machinery never sees it on its own and the rendering happens
    here instead.
    """
    if value is None:
        return ""
    text = str(value)
    if not text.strip():
        return text

    from texsmith.readers.tmark import parse_payload
    import tmark

    payload = parse_payload(text, name="<exam template attribute>")
    return str(tmark.write(payload, backend, {}).get("text") or "").strip()


def parse_box(value: str) -> tuple[str, str] | None:
    """``box=`` as ``(width, height)``; the width is empty for a bare height.

    ``box=50`` reserves a full-width area 50mm high; ``box=6cmx4cm`` a box of
    that width and that height.
    """
    raw = value.strip()
    if not raw:
        return None
    if "x" in raw:
        width_raw, height_raw = raw.split("x", 1)
        width = normalize_box_dim(width_raw)
        height = normalize_box_dim(height_raw)
        return (width, height) if (width and height) else None
    return ("", normalize_box_dim(raw))


def auto_fillin_width(plain: str, scale: float) -> str:
    """The width reserved for a blank whose answer is ``plain``, in millimetres."""
    visible = re.sub(r"\s+", "", plain or "")
    width_mm = max(1, len(visible)) * scale
    if float(width_mm).is_integer():
        return f"{int(width_mm)}mm"
    return f"{width_mm:.2f}".rstrip("0").rstrip(".") + "mm"


def expand_lines_value(value: str, *, unit_macro: str) -> str:
    trimmed = value.strip()
    if trimmed.isdigit():
        return f"{trimmed}\\{unit_macro}"
    return trimmed


def choice_label(index: int) -> str:
    """Return A, B, ..., Z, AA, AB, ... for 0-based index."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = ""
    value = index + 1
    while value:
        value, rem = divmod(value - 1, 26)
        label = alphabet[rem] + label
    return label


def is_truthy_attribute(value: str | None) -> bool:
    if value is None:
        return False
    if value == "":
        return True
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on", "y", "t"}


def is_empty_title(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    cleaned = normalized.replace("\\", "").replace("\u00a0", "")
    compact = "".join(ch for ch in cleaned if not ch.isspace())
    return _EMPTY_TITLE_PATTERN.fullmatch(compact) is not None


def matches_empty_title_pattern(text: str) -> bool:
    return _EMPTY_TITLE_PATTERN.fullmatch(text) is not None


__all__ = [
    "auto_fillin_width",
    "choice_label",
    "expand_lines_value",
    "extract_dash_attrs_prefix",
    "is_empty_title",
    "is_truthy_attribute",
    "markdown_to",
    "matches_empty_title_pattern",
    "normalize_answer_text",
    "normalize_box_dim",
    "normalize_fillin_width",
    "normalize_points",
    "normalize_style_choice",
    "parse_box",
    "parse_heading_attrs",
]

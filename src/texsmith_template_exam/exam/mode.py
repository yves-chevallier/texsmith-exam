"""Helpers for solution/compact mode detection."""

from __future__ import annotations

from pathlib import Path

from texsmith.core.context import RenderContext


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _coerce_bool(value: object, *, default: bool) -> bool:
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


def front_matter_flag(context: RenderContext, keys: tuple[str, ...]) -> object:
    cache_key = "_texsmith_front_matter"
    cached = context.runtime.get(cache_key)
    if cached is None:
        document_path = context.runtime.get("document_path")
        front_matter: dict[str, object] = {}
        if document_path is not None:
            try:
                from texsmith.adapters.markdown import split_front_matter

                raw = Path(document_path).read_text(encoding="utf-8")
                front_matter, _ = split_front_matter(raw)
            except Exception:
                front_matter = {}
        context.runtime[cache_key] = front_matter
        cached = front_matter
    if not isinstance(cached, dict):
        return None
    for key in keys:
        if "." in key:
            cursor: object = cached
            for part in key.split("."):
                if not isinstance(cursor, dict):
                    cursor = None
                    break
                cursor = cursor.get(part)
            if cursor is not None:
                return cursor
        else:
            if key in cached:
                return cached.get(key)
    return None


def in_solution_mode(context: RenderContext) -> bool:
    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        value = overrides.get("solution")
        if _is_truthy(value):
            return True
        press = overrides.get("press")
        if isinstance(press, dict) and _is_truthy(press.get("solution")):
            return True
    value = context.runtime.get("solution")
    if _is_truthy(value):
        return True

    front_matter_value = front_matter_flag(context, ("solution", "exam.solution", "press.solution"))
    if _is_truthy(front_matter_value):
        return True

    # Fallback for project solution builds when overrides are not propagated.
    document_path = context.runtime.get("document_path")
    if document_path is not None:
        path_text = str(document_path).replace("\\", "/").lower()
        if "/solution/" in path_text or path_text.endswith("-solutions.md") or ".solution." in path_text:
            return True
    return False


def in_compact_mode(context: RenderContext) -> bool:
    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        value = overrides.get("compact")
        if _is_truthy(value):
            return True
        press = overrides.get("press")
        if isinstance(press, dict) and _is_truthy(press.get("compact")):
            return True
    value = context.runtime.get("compact")
    if _is_truthy(value):
        return True

    front_matter_value = front_matter_flag(context, ("compact", "exam.compact", "press.compact"))
    if _is_truthy(front_matter_value):
        return True

    # Fallback for project light builds where compact mode is generated in a
    # dedicated source directory before front-matter overrides are propagated.
    document_path = context.runtime.get("document_path")
    if document_path is not None:
        path_text = str(document_path).replace("\\", "/").lower()
        if "/light-src/" in path_text or path_text.endswith("-light.md") or ".light." in path_text:
            return True
    return False


def points_enabled(context: RenderContext) -> bool:
    overrides = context.runtime.get("template_overrides")
    if isinstance(overrides, dict):
        if "points" in overrides:
            return _coerce_bool(overrides.get("points"), default=True)
        exam = overrides.get("exam")
        if isinstance(exam, dict) and "points" in exam:
            return _coerce_bool(exam.get("points"), default=True)
    if "points" in context.runtime:
        return _coerce_bool(context.runtime.get("points"), default=True)
    return _coerce_bool(front_matter_flag(context, ("points", "exam.points")), default=True)


__all__ = ["front_matter_flag", "in_compact_mode", "in_solution_mode", "points_enabled"]

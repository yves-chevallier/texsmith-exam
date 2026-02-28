"""Helpers to resolve exam runtime/config flags consistently."""

from __future__ import annotations

from collections.abc import Mapping

from texsmith.core.context import RenderContext


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


def _nested_lookup(payload: object, dotted_key: str) -> object | None:
    if payload is None:
        return None
    cursor: object = payload
    for part in dotted_key.split("."):
        if isinstance(cursor, Mapping):
            cursor = cursor.get(part)
            continue
        if hasattr(cursor, part):
            cursor = getattr(cursor, part)
            continue
        return None
    return cursor


def _runtime_override_value(context: RenderContext, keys: tuple[str, ...]) -> object | None:
    overrides = context.runtime.get("template_overrides")
    if not isinstance(overrides, dict):
        return None
    for key in keys:
        value = _nested_lookup(overrides, key)
        if value is not None:
            return value
    return None


def _config_value(context: RenderContext, keys: tuple[str, ...]) -> object | None:
    config = getattr(context, "config", None)
    for key in keys:
        value = _nested_lookup(config, key)
        if value is not None:
            return value
    return None


def front_matter_flag(context: RenderContext, keys: tuple[str, ...]) -> object:
    # Front matter should be resolved by TeXSmith and exposed through template_overrides.
    # Keep this fallback only for explicit runtimes in tests/custom integrations.
    payload = context.runtime.get("front_matter")
    if not isinstance(payload, Mapping):
        return None
    for key in keys:
        value = _nested_lookup(payload, key)
        if value is not None:
            return value
    return None


def resolve_value(
    context: RenderContext,
    keys: tuple[str, ...],
    *,
    include_runtime: bool = True,
    include_front_matter: bool = True,
) -> object | None:
    override_value = _runtime_override_value(context, keys)
    if override_value is not None:
        return override_value

    config_value = _config_value(context, keys)
    if config_value is not None:
        return config_value

    if include_runtime:
        for key in keys:
            if "." in key:
                continue
            if key in context.runtime:
                value = context.runtime.get(key)
                if value is not None:
                    return value

    if include_front_matter:
        return front_matter_flag(context, keys)
    return None


def resolve_bool(
    context: RenderContext,
    keys: tuple[str, ...],
    *,
    default: bool,
    include_runtime: bool = True,
    include_front_matter: bool = True,
) -> bool:
    value = resolve_value(
        context,
        keys,
        include_runtime=include_runtime,
        include_front_matter=include_front_matter,
    )
    return _coerce_bool(value, default=default)


def in_solution_mode(context: RenderContext) -> bool:
    return resolve_bool(
        context,
        ("solution", "exam.solution", "press.solution"),
        default=False,
        include_runtime=True,
        include_front_matter=True,
    )


def in_compact_mode(context: RenderContext) -> bool:
    return resolve_bool(
        context,
        ("compact", "exam.compact", "press.compact"),
        default=False,
        include_runtime=True,
        include_front_matter=True,
    )


def points_enabled(context: RenderContext) -> bool:
    return resolve_bool(
        context,
        ("points", "exam.points"),
        default=True,
        include_runtime=True,
        include_front_matter=True,
    )


__all__ = [
    "front_matter_flag",
    "in_compact_mode",
    "in_solution_mode",
    "points_enabled",
    "resolve_bool",
    "resolve_value",
]

"""Helpers for solution/compact mode detection."""

from __future__ import annotations

from collections.abc import Mapping
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


def _source_config_value(context: RenderContext, keys: tuple[str, ...]) -> object | None:
    payload = _source_config_payload(context)
    if payload is None:
        return None
    for key in keys:
        value = _nested_lookup(payload, key)
        if value is not None:
            return value
    return None


def _merge_mappings(base: object, incoming: object) -> object:
    if not isinstance(base, Mapping) or not isinstance(incoming, Mapping):
        return incoming
    merged: dict[object, object] = dict(base)
    for key, value in incoming.items():
        if key in merged:
            merged[key] = _merge_mappings(merged[key], value)
        else:
            merged[key] = value
    return merged


def _source_config_payload(context: RenderContext) -> Mapping[str, object] | None:
    cache_key = "_texsmith_source_config"
    cached = context.runtime.get(cache_key)
    if cached is not None:
        return cached if isinstance(cached, Mapping) else None

    source_dir = context.runtime.get("source_dir")
    if not source_dir:
        context.runtime[cache_key] = False
        return None
    root = Path(str(source_dir))
    candidates = [
        root / "common.yaml",
        root / "common.yml",
        root / "config.yaml",
        root / "config.yml",
    ]
    existing = [path for path in candidates if path.exists() and path.is_file()]
    if not existing:
        context.runtime[cache_key] = False
        return None
    try:
        import yaml
    except Exception:
        context.runtime[cache_key] = False
        return None

    merged: object = {}
    for path in existing:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, Mapping):
            merged = _merge_mappings(merged, payload)

    if not isinstance(merged, Mapping):
        context.runtime[cache_key] = False
        return None
    context.runtime[cache_key] = merged
    return merged


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

    source_value = _source_config_value(context, keys)
    if source_value is not None:
        return source_value

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


def in_solution_mode(context: RenderContext) -> bool:
    value = resolve_value(
        context,
        ("solution", "exam.solution", "press.solution"),
        include_runtime=True,
        include_front_matter=True,
    )
    if _is_truthy(value):
        return True

    # Fallback for project solution builds when overrides are not propagated.
    document_path = context.runtime.get("document_path")
    if document_path is not None:
        path_text = str(document_path).replace("\\", "/").lower()
        if "/solution/" in path_text or path_text.endswith("-solutions.md") or ".solution." in path_text:
            return True
    return False


def in_compact_mode(context: RenderContext) -> bool:
    value = resolve_value(
        context,
        ("compact", "exam.compact", "press.compact"),
        include_runtime=True,
        include_front_matter=True,
    )
    if _is_truthy(value):
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
    value = resolve_value(
        context,
        ("points", "exam.points"),
        include_runtime=True,
        include_front_matter=True,
    )
    return _coerce_bool(value, default=True)


__all__ = [
    "front_matter_flag",
    "in_compact_mode",
    "in_solution_mode",
    "points_enabled",
    "resolve_value",
]

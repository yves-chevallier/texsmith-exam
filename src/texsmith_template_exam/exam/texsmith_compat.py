"""Compatibility layer for texsmith internal helpers."""

from __future__ import annotations

from texsmith.adapters.handlers._helpers import coerce_attribute, mark_processed
from texsmith.adapters.handlers.admonitions import gather_classes
from texsmith.adapters.handlers.blocks import _prepare_rich_text_content
from texsmith.adapters.handlers.code import _is_ascii_art, _resolve_code_engine
from texsmith.adapters.handlers.inline import _payload_is_block_environment
from texsmith.adapters.handlers.media import render_images


__all__ = [
    "coerce_attribute",
    "gather_classes",
    "is_ascii_art",
    "mark_processed",
    "payload_is_block_environment",
    "prepare_rich_text_content",
    "render_images",
    "resolve_code_engine",
]


# Re-export with stable names used by this project.
prepare_rich_text_content = _prepare_rich_text_content
is_ascii_art = _is_ascii_art
resolve_code_engine = _resolve_code_engine
payload_is_block_environment = _payload_is_block_environment

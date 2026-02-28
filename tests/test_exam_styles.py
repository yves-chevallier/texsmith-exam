from __future__ import annotations

from texsmith_template_exam.exam import styles


class _DummyContext:
    def __init__(self, runtime: dict[str, object] | None = None, config: object | None = None) -> None:
        self.runtime = runtime or {}
        self.config = config


def test_choice_style_defaults_and_aliases() -> None:
    ctx = _DummyContext({"template_overrides": {"style": {"choices": "checkboxes"}}})
    assert styles.choice_style(ctx) == "checkbox"


def test_text_style_defaults_and_aliases() -> None:
    ctx = _DummyContext({"template_overrides": {"style": {"text": "line"}}})
    assert styles.text_style(ctx) == "lines"


def test_style_reads_front_matter_runtime_fallback() -> None:
    ctx = _DummyContext(runtime={"front_matter": {"style": {"choices": "checkboxes", "text": "line"}}})
    assert styles.choice_style(ctx) == "checkbox"
    assert styles.text_style(ctx) == "lines"

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


def test_style_reads_source_config_file(tmp_path) -> None:
    source_dir = tmp_path / "series"
    source_dir.mkdir()
    (source_dir / "config.yml").write_text("style:\n  choices: checkboxes\n  text: line\n", encoding="utf-8")
    ctx = _DummyContext(runtime={"source_dir": str(source_dir)})
    assert styles.choice_style(ctx) == "checkbox"
    assert styles.text_style(ctx) == "lines"

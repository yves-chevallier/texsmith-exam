from __future__ import annotations

from texsmith_template_exam.exam import mode


class _DummyContext:
    def __init__(self, runtime: dict[str, object] | None = None, config: object | None = None) -> None:
        self.runtime = runtime or {}
        self.config = config


def test_in_solution_mode_from_overrides_and_path_fallback() -> None:
    assert mode.in_solution_mode(_DummyContext({"template_overrides": {"solution": True}}))
    assert mode.in_solution_mode(_DummyContext({"solution": "true"}))
    assert mode.in_solution_mode(
        _DummyContext({"document_path": "/tmp/build/series/20/solution/series-20.md"})
    )
    assert not mode.in_solution_mode(_DummyContext())


def test_in_compact_mode_from_overrides_and_path_fallback() -> None:
    assert mode.in_compact_mode(_DummyContext({"template_overrides": {"compact": True}}))
    assert mode.in_compact_mode(_DummyContext({"compact": "yes"}))
    assert mode.in_compact_mode(
        _DummyContext({"document_path": "/tmp/build/series/20/light-src/series-20.md"})
    )
    assert not mode.in_compact_mode(_DummyContext())


def test_points_enabled_precedence_runtime_over_config_and_front_matter(tmp_path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("---\nexam:\n  points: false\n---\n# Title\n", encoding="utf-8")

    # 1) Runtime overrides have highest precedence.
    assert mode.points_enabled(
        _DummyContext(
            runtime={
                "template_overrides": {"exam": {"points": "false"}},
                "document_path": str(doc),
            },
            config={"exam": {"points": True}},
        )
    ) is False

    assert mode.points_enabled(
        _DummyContext(
            runtime={
                "template_overrides": {"points": True},
                "document_path": str(doc),
            },
            config={"exam": {"points": False}},
        )
    ) is True

    # 2) Config-level value is used when no runtime override is present.
    assert mode.points_enabled(
        _DummyContext(runtime={"document_path": str(doc)}, config={"exam": {"points": False}})
    ) is False

    # 3) Front matter is fallback when neither runtime nor config provides value.
    assert mode.points_enabled(_DummyContext(runtime={"document_path": str(doc)})) is False

    # 4) Default is true when nothing is provided.
    assert mode.points_enabled(_DummyContext()) is True


def test_points_enabled_reads_attribute_style_config() -> None:
    class _Config:
        exam = {"points": False}

    assert mode.points_enabled(_DummyContext(config=_Config())) is False

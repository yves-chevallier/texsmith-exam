from __future__ import annotations

from bs4 import BeautifulSoup

from texsmith_template_exam.exam import headings


class _DummyState:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    def add_heading(self, level: int, text: str, ref: str | None) -> None:
        return


class _DummyFormatter:
    def heading(self, text: str, level: int, ref: str | None, numbered: bool, points=None) -> str:
        return f"\\section{{{text}}}"

    def pagestyle(self, text: str) -> str:
        return f"\\pagestyle{{{text}}}"


class _DummyConfig:
    legacy_latex_accents = False

    def __init__(self, exam_points: bool | None = None) -> None:
        self.exam = {}
        if exam_points is not None:
            self.exam["points"] = exam_points


class _DummyContext:
    def __init__(self, *, config: object | None = None, runtime: dict[str, object] | None = None) -> None:
        self.config = config or _DummyConfig()
        self.runtime = runtime or {}
        self.state = _DummyState()
        self.formatter = _DummyFormatter()


def _render_heading(*, points_attr: str, config_points: bool, runtime: dict[str, object] | None = None) -> str:
    soup = BeautifulSoup(f"<h3 points='{points_attr}'>Part A</h3>", "html.parser")
    element = soup.find("h3")
    assert element is not None
    headings.render_exam_headings(
        element,
        _DummyContext(config=_DummyConfig(config_points), runtime=runtime),
    )
    return soup.get_text()


def test_render_exam_headings_omits_part_points_when_disabled_in_config() -> None:
    rendered = _render_heading(points_attr="2", config_points=False)
    assert r"\part " in rendered
    assert r"\part[2]" not in rendered


def test_render_exam_headings_keeps_part_points_when_enabled_in_config() -> None:
    rendered = _render_heading(points_attr="2", config_points=True)
    assert r"\part[2]" in rendered


def test_render_exam_headings_runtime_override_has_priority() -> None:
    rendered = _render_heading(
        points_attr="2",
        config_points=False,
        runtime={"template_overrides": {"points": True}},
    )
    assert r"\part[2]" in rendered

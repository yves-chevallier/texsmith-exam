from __future__ import annotations

from bs4 import BeautifulSoup

from texsmith_template_exam import exam_renderer as er


class _DummyConfig:
    legacy_latex_accents = False


class _DummyState:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    def add_heading(self, level: int, text: str, ref: str | None) -> None:
        self.last_heading = (level, text, ref)


class _DummyContext:
    def __init__(self, runtime: dict | None = None) -> None:
        self.runtime = runtime or {}
        self.state = _DummyState()
        self.config = _DummyConfig()

    def suppress_children(self, _element) -> None:
        return

    def mark_processed(self, _element, phase=None) -> None:
        return


def test_normalize_answer_text_handles_quotes_and_backticks() -> None:
    assert er._normalize_answer_text("`(int)0`") == "(int)0"
    assert er._normalize_answer_text('"value"') == "value"
    assert er._normalize_answer_text("« valeur »") == "valeur"
    assert er._normalize_answer_text("  keep  ") == "keep"


def test_extract_dash_attrs_prefix_parses_and_returns_tail() -> None:
    attrs, tail = er._extract_dash_attrs_prefix('- { points=2 answer="ok" } next text')  # type: ignore[misc]
    assert attrs == ' points=2 answer="ok" '
    assert tail == "next text"


def test_parse_heading_attrs_supports_multiple_quote_styles() -> None:
    parsed = er._parse_heading_attrs('points=2 answer="yes" alt=\'ok\' french=«bon»')
    assert parsed["points"] == "2"
    assert parsed["answer"] == "yes"
    assert parsed["alt"] == "ok"
    assert parsed["french"] == "bon"


def test_choice_label_extends_after_z() -> None:
    assert er._choice_label(0) == "A"
    assert er._choice_label(25) == "Z"
    assert er._choice_label(26) == "AA"
    assert er._choice_label(27) == "AB"


def test_solution_env_lines_grid_and_box_variants() -> None:
    begin, end = er._solution_env("2", None, None, "dotted")
    assert begin == r"\begin{solutionordottedlines}[2\dottedlinefillheight]" + "\n"
    assert r"\end{solutionordottedlines}" in end

    begin, end = er._solution_env(None, "3", None, "dotted")
    assert begin == r"\begin{solutionorgrid}[3\linefillheight]" + "\n"
    assert r"\end{solutionorgrid}" in end

    begin, end = er._solution_env(None, None, "4x4", "dotted")
    assert r"\ifprintanswers" in begin
    assert r"\fbox{\parbox[c][4mm][c]{4mm}" in end
    assert r"\hfill" in end


def test_solution_env_fill_mode_switches_by_text_style() -> None:
    begin, end = er._solution_env("fill", None, None, "dotted")
    assert r"\begin{solution}" in begin
    assert r"\fillwithdottedlines{\stretch{1}}" in end

    begin, end = er._solution_env("fill", None, None, "lines")
    assert r"\fillwithlines{\stretch{1}}" in end

    begin, end = er._solution_env("fill", None, None, "box")
    assert r"\makeemptybox{\stretch{1}}" in end


def test_in_solution_mode_from_overrides_and_path_fallback() -> None:
    assert er._in_solution_mode(_DummyContext({"template_overrides": {"solution": True}}))
    assert er._in_solution_mode(_DummyContext({"solution": "true"}))
    assert er._in_solution_mode(
        _DummyContext({"document_path": "/tmp/build/series/20/solution/series-20.md"})
    )
    assert not er._in_solution_mode(_DummyContext())


def test_in_compact_mode_from_overrides_and_path_fallback() -> None:
    assert er._in_compact_mode(_DummyContext({"template_overrides": {"compact": True}}))
    assert er._in_compact_mode(_DummyContext({"compact": "yes"}))
    assert er._in_compact_mode(
        _DummyContext({"document_path": "/tmp/build/series/20/light-src/series-20.md"})
    )
    assert not er._in_compact_mode(_DummyContext())


def test_replace_fillin_placeholders_uses_width_in_pset(monkeypatch) -> None:
    monkeypatch.setattr(er, "render_moving_text", lambda text, *_args, **_kwargs: text)
    soup = BeautifulSoup("<p>Value: [42]{w=30}</p>", "html.parser")
    er._replace_fillin_placeholders(soup, _DummyContext())
    assert r"\fillin[42][30mm]" in soup.get_text()


def test_replace_fillin_placeholders_drops_width_in_solution(monkeypatch) -> None:
    monkeypatch.setattr(er, "render_moving_text", lambda text, *_args, **_kwargs: text)
    soup = BeautifulSoup("<p>Value: [42]{w=30}</p>", "html.parser")
    ctx = _DummyContext({"template_overrides": {"solution": True}})
    er._replace_fillin_placeholders(soup, ctx)
    assert r"\fillin[42]" in soup.get_text()
    assert "[30mm]" not in soup.get_text()


def test_render_table_fillin_cells(monkeypatch) -> None:
    monkeypatch.setattr(er, "render_moving_text", lambda text, *_args, **_kwargs: text)
    soup = BeautifulSoup("<table><tr><td>[ok]{w=12}</td></tr></table>", "html.parser")
    td = soup.find("td")
    assert td is not None
    er.render_table_fillin_cells(td, _DummyContext())
    assert td.get_text() == r"\fillin[ok][12mm]"


def test_render_exam_checkboxes_choices_with_answerline(monkeypatch) -> None:
    monkeypatch.setattr(er, "_prepare_rich_text_content", lambda *_args, **_kwargs: None)
    soup = BeautifulSoup("<div><ul><li>[x] A</li><li>[ ] B</li></ul></div>", "html.parser")
    ul = soup.find("ul")
    assert ul is not None
    er.render_exam_checkboxes(ul, _DummyContext())
    rendered = soup.get_text()
    assert r"\begin{choices}" in rendered
    assert r"\CorrectChoice A" in rendered
    assert r"\choice B" in rendered
    assert r"\answerline[A]" in rendered


def test_render_exam_checkboxes_compact_hides_answerline(monkeypatch) -> None:
    monkeypatch.setattr(er, "_prepare_rich_text_content", lambda *_args, **_kwargs: None)
    soup = BeautifulSoup("<div><ul><li>[x] A</li></ul></div>", "html.parser")
    ul = soup.find("ul")
    assert ul is not None
    er.render_exam_checkboxes(ul, _DummyContext({"compact": True}))
    rendered = soup.get_text()
    assert r"\begin{choices}" in rendered
    assert r"\answerline" not in rendered


def test_render_exam_checkboxes_checkbox_style(monkeypatch) -> None:
    monkeypatch.setattr(er, "_prepare_rich_text_content", lambda *_args, **_kwargs: None)
    soup = BeautifulSoup("<div><ul><li>[x] A</li></ul></div>", "html.parser")
    ul = soup.find("ul")
    assert ul is not None
    ctx = _DummyContext({"template_overrides": {"style": {"choices": "checkbox"}}})
    er.render_exam_checkboxes(ul, ctx)
    rendered = soup.get_text()
    assert r"\begin{checkboxes}" in rendered
    assert r"\end{checkboxes}" in rendered


def test_register_registers_all_handlers() -> None:
    registered: list[str] = []

    class _Renderer:
        def register(self, fn) -> None:
            registered.append(fn.__name__)

    er.register(_Renderer())

    assert "set_exam_callouts" in registered
    assert "render_exam_headings" in registered
    assert "close_open_parts" in registered
    assert "render_pending_answerline_paragraph" in registered


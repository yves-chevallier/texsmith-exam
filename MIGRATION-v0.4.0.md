# Migration plan — `texsmith-exam` → texsmith v0.4.0 (and Typst)

Status: **design / for review — no code changes yet.**
Author: drafted with Claude Code, 2026-06-27.

---

## 0. Executive summary

texsmith v0.4.0 replaced the old "mutate the BeautifulSoup tree" pipeline
(`texsmith.core.rules`, `@renders`, `RenderContext`, `texsmith.adapters.handlers.*`)
with a typed-IR pipeline: **read(HTML) → IR → write(IR)**. The exam template is
built almost entirely on the removed layer, so it does **not import** under 0.4.0
(`ModuleNotFoundError: texsmith.core.rules`). ~192 references to removed APIs across
9 modules / ~2 800 LOC; ~17 registered `@renders` handlers.

Two findings shape the whole effort:

1. **Blocking prerequisite (upstream).** v0.4.0 has **no supported extension hook**
   for a third-party package to contribute `@reads`/`@writes` rules. The renderer
   exposes the seams (`LaTeXRenderer.reader_registry`, `LaTeXRenderer.writer_class`)
   but the conversion pipeline **never populates them**, and the only entry-point
   group consumed at runtime is `texsmith.fragments`. The old `texsmith.renderers`
   group is gone with **no replacement**. ⇒ The exam template cannot inject its
   custom rendering on 0.4.0 until texsmith itself gains an extension hook
   (**Phase 0** below). Since we own texsmith, this is a small, clean addition.

2. **Asymmetric scope.** LaTeX compat is a real but bounded migration. Typst is
   near green-field: `exam.cls` is LaTeX-only with no Typst equivalent, so every
   exam construct (questions, parts, choices, fill-ins, solution boxes, grade
   table) must be re-implemented in Typst from scratch — a larger effort, on a
   backend that is itself experimental in 0.4.0.

Recommended sequencing: **Phase 0 (texsmith hook) → Phase 1 (LaTeX migration) →
Phase 2 (Typst, separate, optional).**

---

## 1. What survives untouched

- **`solution_md.py`** — a standard python-markdown `Extension`/`Preprocessor`
  (`!!! solution {…}` → `<div class="texsmith-solution" …>`). Pure
  python-markdown; **no change needed**.
- **`markdown.py`** — appends the solution extension to
  `DEFAULT_MARKDOWN_EXTENSIONS`. Only depends on `texsmith.adapters.markdown`
  (`DEFAULT_MARKDOWN_EXTENSIONS`, `deduplicate_markdown_extensions`,
  `render_markdown`) — confirm those symbols still exist in 0.4.0 (they do as of
  the IR migration), otherwise trivial.
- **`exam/utils.py`** — pure helpers (`choice_label`, `expand_lines_value`,
  `parse_heading_attrs`, `normalize_*`, `is_empty_title`, …). Portable as-is.
- **`exam/fillin.py`** width math, **`exam/mode.py`**, **`exam/styles.py`** — depend
  only on a context-like object for `template_overrides`/config/front-matter
  lookups; portable once the "context" is replaced by the new `WriterState`
  (same attribute shape: `.config`, `.runtime`, `.state`).
- **The template manifest + Jinja `template.tex` + fragments** (`ts-geometry`,
  `ts-fonts`, `ts-callouts`, …) and the **`texsmith.templates` / `texsmith.fragments`
  entry points** — the fragment & template systems are intact in 0.4.0.
- **`heiglogo.sty` / `columen.sty`** assets — unchanged.

## 2. What must change

| Area | Old (removed) | New (0.4.0) |
|---|---|---|
| Rule registration | `texsmith.renderers` entry point → `register(renderer)` | **no entry point** — needs Phase 0 hook |
| HTML handling | `@renders(tag, phase=…)` mutating soup | `@reads(*tags, level, priority)` → returns IR node(s) |
| Output | mutate soup into LaTeX strings | `@writes(NodeType)` on a `LaTeXWriter` subclass → returns str |
| Context | `RenderContext` (`.state`, `.runtime`, `.formatter`, `.mark_processed`) | `WriterState` (`.state`, `.runtime`, `.formatter`, `.assets`, `.config`) |
| Helpers | `texsmith.adapters.handlers.*` (`texsmith_compat.py`) | see §6 relocation table |
| Cross-node state | `context.state.counters`, `context.runtime[...]` | `WriterState.state.counters` / `.runtime`, harvested in a pre-pass over the IR |
| Template overrides bridge | monkeypatch of `_build_runtime_common` | supported override surfacing (Phase 0) |

---

## 3. Phase 0 — Upstream texsmith extension hook (prerequisite)

**Problem.** `core/conversion/core.py` builds the renderer and never sets
`reader_registry`/`writer_class`; nothing discovers third-party `@reads`/`@writes`.

**Proposed addition to texsmith (0.4.x, additive, non-breaking).** Add two
entry-point groups discovered in the conversion pipeline and used to populate the
existing renderer seams:

```
[project.entry-points."texsmith.readers"]
exam = "texsmith_template_exam.reader:collect"      # returns modules / a ReaderRegistry

[project.entry-points."texsmith.writers"]
exam = "texsmith_template_exam.writer:ExamLaTeXWriter"   # a LaTeXWriter subclass (or mixin)
```

Pipeline wiring (sketch, in `core.py` near the `renderer_factory`):

```python
renderer.reader_registry = build_reader_registry_from_entry_points()   # collect_from each
renderer.writer_class    = compose_writer_class_from_entry_points(LaTeXWriter)
```

Design decisions to settle in Phase 0:
- **Scoping**: global (all conversions) vs **template-scoped** (only when the
  selected template opts in). Template-scoped is cleaner and matches how the exam
  rules should only apply to exam documents. Could be expressed as a manifest key
  (`[latex.template] readers = [...] / writers = [...]`) or by binding the
  entry point to the template name.
- **Writer composition**: single subclass vs multiple mixins (several plugins
  each adding `@writes`). A registry-merge (collect `@writes` from N classes into
  the active writer's registry) is most flexible.
- **Typst parity**: mirror with `writer_class` for `TypstWriter` (Phase 2).
- **Override surfacing**: provide a supported way to read `template_overrides`
  from `WriterState.runtime` so the exam package can drop its monkeypatch of
  `_build_runtime_common`. Ideally the pipeline already injects
  `runtime["template_overrides"]`; confirm and document.

**Estimate:** ~0.5–1 day in texsmith + tests; ship as 0.4.1.

---

## 4. Phase 1 — LaTeX migration of `texsmith-exam`

### 4.1 New package shape

```
reader.py     # @reads lowerings → IR (Div/Span roles + RawBlock), + collect()
writer.py     # ExamLaTeXWriter(LaTeXWriter) with @writes overrides/additions
state.py      # exam pre-pass helpers (parts/subparts accounting) over the IR
exam/…        # utils.py, fillin.py, mode.py, styles.py kept (context → WriterState)
```

Drop `exam_renderer.py` and `exam/texsmith_compat.py`. Keep `solution_md.py`,
`markdown.py`, `utils.py`.

### 4.2 IR modelling strategy — prefer generic roles over new node types

The IR is a sealed hierarchy; the documented design rule favours the generic
escape hatch for third parties. Use:

- **`Span` / `Div` with `attrs["role"]`** for structured exam constructs, and
  branch on the role inside an `ExamLaTeXWriter` override of `_render_div` /
  `_render_span`. Roles to introduce:
  `exam-question`, `exam-part`, `exam-subpart`, `exam-subsubpart`,
  `exam-choices`, `exam-fillin`, `exam-solution`.
- **`RawBlock("latex", …)` / `RawInline("latex", …)`** for fully-opaque emission
  (e.g. a computed `\fillin[…][…]`, env begin/end markers) when there is no
  child content the writer must recurse into.

This needs **zero IR changes in texsmith** and degrades gracefully (unknown role
renders children transparently). Only escalate to a real typed node if a
construct proves to need structured fields the writer must reason about.

### 4.3 Handler → reader/writer mapping

| Old handler (phase) | New form |
|---|---|
| `set_exam_callouts` (PRE) | one-time setup: register the `solution` callout in `WriterState.runtime["callouts_definitions"]` from the writer's `__init__`/pre-pass (no per-element rule) |
| `render_fillin_placeholders` (DOC PRE, before escape) | `@reads` on text/inline: lower `[answer]{w=}` → `Span role="exam-fillin"` (carry answer + width attrs). Writer emits `\fillin[…][…]`. Replaces the "before escape_plain_text" ordering — lowering happens before writing, so escaping is moot |
| `render_table_fillin_cells` (td/th PRE) | same `exam-fillin` lowering applies inside table cells (reader handles `td`/`th` children) |
| `render_exam_fillin` (span POST) | `@reads("span")`: `class~=texsmith-fillin` → `Span role="exam-fillin"` |
| `render_exam_checkboxes` (ul INLINE) | `@reads("ul")`: detect task list → `Div role="exam-choices"` carrying items (checked flag + inline content) and a `style` attr. Writer emits `choices`/`checkboxes` + `\answerline`. (Self-contained; good first slice.) |
| `strip_fenced_code_in_pre` / `_in_blocks` (PRE) | `@reads("pre")`/`@reads("div.highlight")`: split nested ``` fences into a sequence of `Para`/`CodeBlock` IR nodes (reuse core code lowering); writer side handled by stock `@writes(CodeBlock)` |
| `render_solution_math_*` (div/script/p) | likely **obsolete**: in the IR path, `Math` is a first-class inline/block node; verify math inside solution blocks survives lowering and drop these unless a gap remains |
| `render_solution_admonition` (p BLOCK) | `@reads`: the `!!! solution` / `texsmith-solution` div → `Div role="exam-solution"` with parsed `lines`/`grid`/`box` attrs and lowered body. Writer emits `_solution_env(...)` begin/end around the body |
| `render_solution_callouts` / `promote_solution_admonitions` / `render_solution_div_admonitions` | collapse into the single `exam-solution` lowering above (all three currently normalise different HTML shapes into the same solution env) |
| `render_exam_image_paragraphs` / `render_exam_images` | likely **obsolete**: stock `@writes(Image)`/`@writes(Figure)` handle images, including inside divs. Verify solution-embedded images render; only add a writer tweak if needed |
| `render_pending_answerline_paragraph` (p POST) | folded into the heading pre-pass (see §4.4): deferred answerline becomes an IR node placed after the first `Para` of the question |
| `render_exam_headings` (h1–h6 POST) + `close_open_parts` (doc POST) | **the hard part** — see §4.4 |

### 4.4 The heading → question/parts state machine (hardest)

Old: a single-pass soup walk used `counters[exam_parts_open|subparts_open|subsubparts_open]`
to open/close `parts`/`subparts`/`subsubparts` envs, with `heading_mode_level`
to toggle out to plain headings, deferred answerlines, and label/points parsing.

Two viable strategies in the IR model:

- **(A) Pre-pass that rewrites the IR (recommended).** Add an `ExamLaTeXWriter`
  pre-pass (mirroring how the core writer pre-collects footnotes via
  `texsmith.ir.visitor.walk`) that scans the `Document`'s `Header` nodes and
  rewrites the block sequence into explicit, *already-nested* exam structure:
  `Div role="exam-question"` containing `Div role="exam-part"` … This turns the
  implicit open/close bookkeeping into an explicit tree built **once**, after
  which the `@writes` emitters are simple (emit `\begin{parts}`…`\end{parts}`
  around children). State lives only in the pre-pass, not across emitters.
- **(B) Stateful emitter.** Keep the open/close counters on `WriterState.state`
  and emit begin/end as `Header`-role nodes are visited, closing leftovers at
  document end. Closer to the current code (faster to port) but keeps the fragile
  cross-node state. Acceptable as a first cut; refactor to (A) later.

Either way, port verbatim from `headings.py`: rendered-level math
(`level + base_level − 1`), empty-title detection, points gating, label slugging
(`context.state.add_heading` → `WriterState.state.add_heading`), and the
answerline placement rules (immediate vs deferred on bare-dash titles).

Remove the module-global `_configure_heading_patterns` injection (compile the
regexes in the reader module directly).

### 4.5 `WriterState` vs `RenderContext` for the kept helpers

`mode.py` / `styles.py` / `fillin.py` read `context.runtime["template_overrides"]`,
`context.config.*`, `context.state.*`. `WriterState` exposes the same
(`.runtime`, `.config`, `.state`), so these port by changing the type hint and
the import. `render_moving_text(text, context, …)` still exists in
`texsmith.fonts.scripts` and accepts a `RenderContextLike`; `WriterState`
satisfies that protocol, so pass `self.state`.

### 4.6 Helper relocation table (`texsmith_compat.py` → 0.4.0)

| Old (`adapters.handlers.*`) | 0.4.0 |
|---|---|
| `coerce_attribute` | `texsmith.adapters.html_utils.coerce_attribute` (reader-side: `readers.html._helpers.coerce_attr`) |
| `gather_classes` | `texsmith.adapters.html_utils.gather_classes` (reader-side: `readers.html._helpers.classes`) |
| `mark_processed` | **gone, no replacement** — obsolete (dispatch is by `(level, tag)` + `NotHandled`, not soup marking) |
| `prepare_rich_text_content` | **gone** — use `ctx.lower_inline(...)` in the reader; emit with the writer's inline rendering |
| `is_ascii_art` | now `texsmith.writers.latex.writer._is_ascii_art` (module-private; copy into the exam writer if needed) |
| `resolve_code_engine` | now `LaTeXWriter._code_engine` (reads `runtime["code"]["engine"]`) |
| `payload_is_block_environment` | now `texsmith.writers.latex.writer._payload_is_block_environment` |
| `render_images` | **gone as a function** — stock `@writes(Image)`/`@writes(Figure)` |
| `context.formatter.codeblock(...)` | `self.state.formatter.render_template("codeblock", …, state=self.state.state)` |

(Several of these are module-private in texsmith. Either vendor small copies into
the exam package or, better, ask texsmith to export the stable ones — decide in
Phase 0.)

### 4.7 Drop the monkeypatch

`exam/__init__.py` monkeypatches `conversion_core._build_runtime_common` to copy
`template_overrides` into `runtime`. Replace with the supported override
surfacing decided in Phase 0; remove the monkeypatch.

### 4.8 Tests

Existing tests target the old API (`RenderContext`, `@renders`) and will be
rewritten. Strategy: keep the **input Markdown → expected LaTeX** assertions
(those encode the real contract) and re-point them at the new
read→write path (render via a configured `LaTeXRenderer` with the exam
reader/writer). The `demo/exam`, `demo/quiz`, `demo/pset` documents become
golden end-to-end fixtures (compile under lualatex + exam.cls).

---

## 5. Phase 2 — Typst backend (optional, experimental, green-field)

`exam.cls` has **no Typst equivalent**. To support `--format typst` for exams:

- Add a `[typst.template]` section + `template.typ` to the manifest (parallel to
  the article/book templates that already ship Typst scaffolding in 0.4.0).
- Re-implement, in Typst, every exam construct currently delegated to exam.cls:
  question/part/subpart numbering, choices/checkboxes with answer reveal,
  fill-ins, solution boxes/lines/grids with a print-answers toggle, points and
  the cover grade table. This is genuine typesetting work with no upstream
  scaffolding to lean on.
- Provide `@writes(...)` Typst emitters for the same exam roles
  (`exam-question`, `exam-choices`, `exam-fillin`, `exam-solution`) on a
  `TypstWriter` subclass, wired via the Phase 0 hook's Typst counterpart.
- Accept the 0.4.0 Typst caveats (math via `mitex`, etc.).

**Estimate:** comparable to or larger than Phase 1; recommend only after Phase 1
ships and stabilises. Could begin with a reduced feature set (questions + choices
+ solutions on/off) and grow.

---

## 6. Risks & open questions

1. **No 0.4.0 extension hook (Phase 0)** — hard blocker; must land first.
2. **Heading state machine** — the deferred-answerline + heading-mode toggle +
   nested env open/close is intricate; strategy (A) (pre-pass to nested IR) de-risks
   it but is the bulk of the work.
3. **Private texsmith helpers** — a few needed helpers are module-private; decide
   export-vs-vendor in Phase 0.
4. **Math-in-solution & images-in-solution** — verify whether the stock IR path
   already covers what the old PRE/POST math/image handlers patched; only port the
   genuine gaps.
5. **`render_solution_math_scripts` is decorated but NOT registered** — confirm
   that omission is intentional before reproducing it.
6. **Two divergent `_solution_env` copies** (`exam_renderer.py` vs `solutions.py`,
   the latter referencing an imported `text_style` symbol rather than a value) —
   reconcile into one during the move; likely a latent bug to fix.
7. **CI** — the package CI installs texsmith from PyPI; pin/bump to 0.4.x once the
   hook ships.

---

## 7. Recommended sequence & estimate

1. **Phase 0** (texsmith 0.4.1): extension hook + override surfacing. ~0.5–1 day.
2. **Phase 1** (texsmith-exam LaTeX): wiring → checkboxes (vertical slice) →
   fill-ins → solutions → headings state machine → drop compat/monkeypatch →
   rewrite tests → golden demos. ~3–5 days.
3. **Phase 2** (Typst): separate, experimental, ~3–6 days; optional.

Total LaTeX-compat path (Phases 0–1): ~1 week of focused work. Typst roughly
doubles it.

---

## 8. Decision points for review

- Approve the **Phase 0 hook design** (entry-point groups vs template-scoped
  manifest keys; writer composition model).
- Approve **role-based IR** (Div/Span roles) over custom IR node types.
- Approve **pre-pass (strategy A)** vs **stateful emitter (strategy B)** for the
  heading machine (recommend A; B acceptable as interim).
- Confirm whether **Typst (Phase 2)** is in scope now or deferred.

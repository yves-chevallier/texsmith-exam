# TeXSmith Exam Template

This project provides an exam template for TeXSmith. It includes an exam-centric
LaTeX renderer with callouts and a structure tailored for assessments.

The template is currently tailored for [HEIG-VD](https://heig-vd.ch). The
long-term goal is to offer a more generic version with configurable branding
(logos, color palettes, and similar options).

## Installation

Add the template as a dependency and install the required dependency groups:

```bash
uv sync --group dev --group docs
```

## Quick start

Use the `exam` template with TeXSmith:

```bash
texsmith render --template exam exam.md
```

Enable solution mode when rendering to build the answer key:

```bash
texsmith render --template exam -a solution=true exam.md
```

## Backends

The same sources render to LaTeX (the default) or to Typst:

```bash
texsmith --template exam config.yml *.md --build
texsmith --format typst --template exam config.yml *.md --build
```

Both backends read the exam constructs through the same IR pass and print the
same exam: the cover page with its grade table and rules box, the questions and
their parts, the multiple choices, the blanks and the space reserved for an
answer, in exam mode and in solution mode alike. Two things are the LaTeX
backend's only:

- a part's body is indented under its label — Typst refuses a page break inside
  a container, and a `---` or a `newpage=true` inside a question is one;
- a `latex` raw block (```` ```latex ````) is dropped by the Typst writer, as a
  `typst` raw block is dropped by the LaTeX one. A page break written that way
  is a `---` on both.

## Title page

By default the template generates a dedicated cover page with the duration,
grade table, and rules. To render a minimal inline title instead, set
`exam.titlepage` to `minimal` in the front matter:

```yaml
exam:
  titlepage: minimal
```

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

## Title page

By default the template generates a dedicated cover page with the duration,
grade table, and rules. To render a minimal inline title instead, set
`exam.titlepage` to `minimal` in the front matter:

```yaml
exam:
  titlepage: minimal
```

# Configuration

This page documents all template configuration options supported by the `exam`
template.

You can set options in document front matter, for example:

```yaml
title: Midterm
date: 2026-02-23
exam:
  titlepage: cover
  course: Algorithms
  duration: 90
  rules:
    - No phones.
```

You can also override values at render time with TeXSmith template overrides
(for example `-a solution=true`).

## Core template options

| Option | Type | Default | Accepted values | Description |
| --- | --- | --- | --- | --- |
| `title` | string | `""` | any string | Exam title (from metadata or promoted heading). |
| `author` / `authors` | string, mapping, or list | `""` | string or structured author data | Author or instructor name(s). |
| `date` | string | `""` | ISO date/time or free text | Exam date shown on title page/header. |
| `exam.titlepage` / `titlepage` | string | `"cover"` | `cover`, `minimal` | Selects full cover page or minimal inline title block. |
| `exam.type` / `type` | string | `"exam"` | any string | Exam type label (for example `TE`, `Exam`). |
| `exam.department` / `department` | string | `""` | any string | Department code or name. |
| `exam.school` / `school` | string | `""` | any string | School or institution name. |
| `exam.course` / `course` | string | `""` | any string | Course name or course code. |
| `exam.problem-label` / `exam.problem_label` / `problem-label` / `problem_label` | string | language-dependent default (`Problem`, `Problème`, etc.) | any string | Overrides the question label used in headers and question titles. |
| `exam.fillin-style` / `exam.fillin_style` / `fillin-style` / `fillin_style` | string | `"line"` | `line`, `dotted` | Controls the visual style of `\fillin` blanks on the student copy. |
| `exam.compact` / `compact` | boolean | `false` | `true`, `false` | Enables compact rendering mode (for example removes some answer lines in multiple-choice blocks). |
| `exam.duration` / `duration` | any | `""` | number or string | Exam duration, displayed on the cover page rules box. |
| `exam.rules` / `rules` | list | `[]` | list of strings/Markdown fragments | Rules shown on the cover page. |
| `exam.solution` / `solution` | boolean | `false` | `true`, `false` | Enables solution mode (`\printanswers`). |
| `language` | string | `"english"` | Babel language names/aliases | Document language passed to Babel (normalized by TeXSmith). |
| `press.paper` / `paper` | mapping | `{ format: a4, margin: { top: 10mm, left: 2.5cm, right: 2.5cm, bottom: 2.5cm } }` | TeXSmith paper mapping | Page format and margin defaults. |
| `press.geometry` / `geometry` | mapping | `{ headheight: 0mm, headsep: 0mm, includeheadfoot: true }` | TeXSmith geometry mapping | Extra geometry options forwarded to `ts-geometry`. |
| `hyperref_options` / `ts_extra_hyperref_options` | string | `"hidelinks"` | any hyperref option string | Options passed to `hyperref` through `ts-extra`. |

## Additional supported options

These options are implemented by the template/renderer and are supported, even
if they are not currently declared in `manifest.toml` as first-class
attributes.

| Option | Type | Default | Accepted values | Description |
| --- | --- | --- | --- | --- |
| `subtitle` | string | `""` | any string | Subtitle shown on title page (cover and minimal modes). |
| `next_page_advice` | boolean-like | `true` | `true`/`false` (or truthy strings) | Controls footer hint text on non-final pages (`Go to the next page...`). |
| `exam.fillin_solution_underline` / `exam.fillin-solution-underline` / `fillin_solution_underline` | boolean | `false` | `true`, `false` | In solution mode, keeps an underline under fill-in answers instead of answer text only. |

## Renderer style overrides

The renderer accepts style overrides through template overrides (for example via
`-a`).

| Option | Type | Default | Accepted values | Description |
| --- | --- | --- | --- | --- |
| `style.choices` | string | `"alpha"` | `alpha`, `checkbox` (`checkboxes`, `check` are aliases) | Multiple-choice rendering style (`choices` vs `checkboxes`). |
| `style.text` | string | `"dotted"` | `dotted`, `lines`, `box` (`dots`, `line`, `dottedlines` are aliases) | Default solution-space style for `!!! solution { lines=... }`. |
| `char-width-scale` | float | `2.5` | positive number | Global scale for automatic width of `[answer]{...}` fill-ins when width is omitted. |
| `fillin_char_width_scale` | float | `2.5` | positive number | Alias of `char-width-scale`. |
| `style.char-width-scale` | float | `2.5` | positive number | Scoped alternative for fill-in auto-width scale. |
| `fillin.char-width-scale` | float | `2.5` | positive number | Scoped alternative for fill-in auto-width scale. |

Compatibility note: `press.solution` and `press.compact` are also recognized by
the renderer as fallback locations for `solution` and `compact`.

## Complete example

```yaml
title: Demo Exam
subtitle: Various questions
author: Dr. Emmett L. Brown
date: 2026-02-23
language: en

press:
  paper:
    format: a4
    margin:
      top: 12mm
      left: 2.4cm
      right: 2.4cm
      bottom: 2.4cm
  geometry:
    includeheadfoot: true

exam:
  titlepage: cover
  type: TE
  department: TIN
  school: HEIG-VD
  course: General Knowledge
  problem-label: Question
  fillin-style: dotted
  duration: 90
  rules:
    - Write your name on each page.
    - No communication devices allowed.
```

# Template syntax

This template extends TeXSmith with a few exam-specific Markdown helpers.

## Headings

Because exams are structured as questions and parts, the usual Markdown
headings map to `question`, `part`, and `subpart` entries in the LaTeX output.
In Markdown, you just use headings as usual. Example:

```md
# Exam Title

## Question 1

### Part 1.1

#### Subpart 1.1.1

### Part 1.2

## Question 2
```

Often you need a part or subpart with no visible title. Use `-` as the heading
text to keep the structure while hiding the title:

```md
## Question

### -

Text for part 1

### -

Text for part 2

#### -

Text for subpart 1 of part 2
```

!!! info

    The `-` label resembles a list marker and keeps Markdown headings
    non-empty, so they still parse correctly.

If you need plain LaTeX sectioning (instead of exam questions/parts), mark a
heading with `{heading=true}`. The marked heading and its subheadings are
rendered with TeXSmith's standard `\section`, `\subsection`, etc.

```md
## Context {heading=true}

### Model

### Variables
```

## Multiple choice

Markdown (and TeXSmith) supports task lists like `- [ ]`. With this template,
task list items are rendered as multiple-choice answers.

```md
## Volcanoes

Which volcanoes are located in Italy? (multiple answers)

- [x] Etna
- [ ] Krakatoa
- [x] Vesuvius
- [ ] Mauna Loa
- [ ] Fuji
- [x] Stromboli
- [ ] Kilauea
```

Checked entries are treated as correct answers. They appear only in the answer
key, not on the student copy.

You do not need to manage layout manually: the
[columen](https://github.com/yves-chevallier/columen) LaTeX package arranges
answers into columns based on available space.

## Fill-in blanks

Inline fill-ins turn into exam-style answer blanks:

```md
The capital of Switzerland is [Bern]{w=30}.
```

The optional attribute block lets you specify the blank width. By default, the
width is computed from the answer text. If you want to avoid revealing the
expected length, set an explicit width (`w=1cm`, `w=1in`, or similar). Both
`width` and `w` are accepted.

In the front matter you can configure `exam.char-width-scale` to scale the
automatic width when no explicit size is provided.

## Solution blocks

Use admonitions to provide solutions and mark answers.

```md
!!! solution

    Solution content appears only in the answer key
```

For short answers, you can request lined space. In the answer key the lines are
replaced by the solution text.

```md
!!! solution { lines=3 }

    Solution text...
```

Sometimes you need a grid instead of dotted lines.

```md
## -

Draw an equilateral triangle

!!! solution { grid=3cm }

    ![Triangle]{triangle.svg}
```

Or you can reserve an empty box for drawings or other free-form answers.

```md
## -

Draw a sheep:

!!! solution { box=5cm }

    Here is an example of the expected drawing:

    ![Sheep]{sheep.svg}

    The result should resemble a sheep with wool and four legs.
```

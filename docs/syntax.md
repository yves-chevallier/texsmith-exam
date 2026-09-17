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

## Points and answer lines

Attach an attribute block in braces to a heading to set the points awarded for a
question or part and, optionally, a short expected answer:

```md
## Capitals { points=2 answer="Bern" }

What is the capital of Switzerland?
```

- `points=` sets the marks for the question or part. Point display is controlled
  globally by the `exam.points` setting; per-question values are only shown when
  it is enabled.
- `answer=` provides a short answer. It is rendered as an answer line on the
  student copy and filled in on the answer key.

The attribute block works on any heading level, so questions, parts, and
subparts can all carry points and answers. It combines with the `-` empty title:

```md
### - { points=2 answer="42" }

What is the answer to the ultimate question?
```

The attribute block is *trailing*: the title comes first and the braces close
the line, so a named part with points reads

```md
### Warm-up { points=2 }

A short introductory question.
```

Answer values may be wrapped in straight quotes, single quotes, French
guillemets `«…»`, curly quotes, or backticks; the surrounding pair is stripped.
Quotes are only required when the value contains spaces — `answer="Mont Blanc"`,
`answer='Bern'`, `answer=«oui»`, and `answer=42` are all valid.

!!! info

    Surrounding whitespace and quotes are trimmed. An empty answer
    (`answer=""` or whitespace only) produces no answer line, whereas
    `answer="0"` shows `0`. Unrecognized attributes are ignored silently, so
    watch for typos such as `ponts=`.

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

The attribute block sets the blank width. Without it the width is computed from
the answer text; if you want to avoid revealing the expected length, set an
explicit width (`w=1cm`, `w=1in`, or similar). Both `width` and `w` are
accepted, and a bare number is read as millimetres.

For an auto-sized blank, mark the span with the `fillin` class — an attribute
block is what makes TMark read `[…]` as a span at all:

```md
The capital of Switzerland is [Bern]{.fillin}.
```

A bare `[Bern]`, with no attribute block, is read as a blank too. TMark leaves
it as literal text, and the template's pass picks it up; set
`exam.fillin-bare: false` in the front matter if a document needs its brackets
back.

In the front matter you can configure `exam.char-width-scale` to scale the
automatic width when no explicit size is provided.

## Solution blocks

A solution is a container: the answer, and the space reserved for it on the
student copy.

```md
::: solution
Solution content appears only in the answer key
:::
```

For short answers, request lined space. In the answer key the lines are
replaced by the solution text.

```md
::: solution {lines=3}
Solution text...
:::
```

`lines=fill` reserves the rest of the page rather than a fixed number of lines.
The line style (dotted, lined or boxed) follows the `style.text` setting.

Sometimes you need a grid instead of dotted lines.

```md
## -

Draw an equilateral triangle

::: solution {grid=3cm}
![Triangle](triangle.svg)
:::
```

Or you can reserve an empty box for drawings or other free-form answers.

```md
## -

Draw a sheep:

::: solution {box=5cm}
Here is an example of the expected drawing:

![Sheep](sheep.svg)

The result should resemble a sheep with wool and four legs.
:::
```

A single value makes a square box; use `box=WxH` (for example `box=8cmx4cm`) to
reserve a rectangle.

An **empty** solution block reserves space and prints nothing in the answer
key — the way to leave a blank page for rough work:

```md
::: solution {lines=fill newpage=true}
:::
```

!!! info "Spelling"

    `::: solution` is not one of TMark's container names, so the parser warns
    (`container-unknown`) before any template is involved and renders the
    content transparently. Two spellings avoid the warning and mean exactly the
    same thing to this template: `::: div {.solution lines=3}`, and `::: solution`
    with `solution` declared under `press.declare.admonitions` in the front matter.

## Page breaks

A thematic break starts a new page:

```md
Text of the last question.

---

# Next question
```

A `---` on the *first* line of a file opens the front matter instead, so a
question that must start on a fresh page says so on its heading:

```md
# Functions { points=15 newpage=true }
```

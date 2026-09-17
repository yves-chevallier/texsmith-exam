{# Typst scaffolding of the TeXSmith "exam" template — the twin of template.tex.

   What exam.cls gives the LaTeX side (question numbering, parts, the space an
   answer is written in, the grade table, the running head and foot) is written
   out here as `#exam-…` functions, so `passes/typst.py` can emit calls as short
   as the `\question` / `\part` / `\fillin` the LaTeX emitter writes.

   Standard Jinja delimiters. `prelude` is the texsmith.typ contract library and
   `body` the document: a `#let ts-…` override has to sit between the two. #}
{% if uses_mitex %}
#import "@preview/mitex:0.2.7": mi, mitex
{% endif %}
{% set lang = language | default('en') | lower %}
{% set minimal = titlepage | default('cover') | lower == 'minimal' %}
{% set geometry = paper.get('margin', {}) if paper is mapping else {} %}
{% set margin_top = geometry.get('top', '10mm') %}
{% set margin_bottom = geometry.get('bottom', '25mm') %}
{% set margin_left = geometry.get('left', '25mm') %}
{% set margin_right = geometry.get('right', '25mm') %}
{% set type_label = "Travail Écrit" if type | lower in ('te', 'travail ecrit', 'travail écrit') else type %}
{% set display_title = title if title else (type_label ~ ' ' ~ course) | trim %}
{% set header_parts = [title, subtitle] if minimal else [school, title] %}
{% set header_left = header_parts | select | join(' / ') %}
{% set logo_choice = logo | default('') %}
{% set logo_off = logo_choice is boolean and not logo_choice
                  or logo_choice is string and logo_choice | lower in ('none', 'false', 'off', 'no') %}
{% set logo_file = logo_choice.get('file', '') if logo_choice is mapping else '' %}
{% set vintage = logo_year if logo_year in ('1998', '2004', '2009', '2020') else logo_vintage %}

// ---------------------------------------------------------------------------
// What the document asked for. Everything below reads these and nothing else.
// ---------------------------------------------------------------------------

#let exam-solution-mode = {{ 'true' if solution else 'false' }}
#let exam-compact = {{ 'true' if compact else 'false' }}
#let exam-points-enabled = {{ 'true' if points else 'false' }}
#let exam-text-style = "{{ style_text }}"
#let exam-choice-style = "{{ style_choices }}"
#let exam-fillin-style = "{{ fillin_style | lower }}"
#let exam-next-page-advice = {{ 'true' if next_page_advice else 'false' }}
#let exam-recto-name = {{ 'true' if recto_name and not solution else 'false' }}
// Room reserved above the text for the running head. Typst keeps the margin on
// every page, but page 1 carries no running head, so the title block claws it
// back — the negative skip `\@maketitle' uses on the LaTeX side.
#let exam-head-room = 15mm
#let exam-margin = (
  top: {{ margin_top }} + exam-head-room,
  bottom: {{ margin_bottom }},
  left: {{ margin_left }},
  right: {{ margin_right }},
)

{% if lang in ('fr', 'french', 'francais', 'français') %}
#let exam-problem-label = "{{ problem_label or 'Problème' }}"
#let exam-point-words = ("point", "points")
#let exam-rules-label = "Consignes"
#let exam-next-page = "Allez à la page suivante..."
#let exam-page-of = ("Page ", " sur ")
#let exam-name-label = "Nom, Prénom"
#let exam-duration = ("Durée du travail ", " minutes.")
#let exam-weekdays = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
#let exam-months = (
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)
#let exam-grade-words = ("Question", "Points", "Score", "Total :")
{% elif lang in ('de', 'german', 'deutsch') %}
#let exam-problem-label = "{{ problem_label or 'Aufgabe' }}"
#let exam-point-words = ("Punkt", "Punkte")
#let exam-rules-label = "Hinweise"
#let exam-next-page = "Bitte zur nächsten Seite..."
#let exam-page-of = ("Seite ", " von ")
#let exam-name-label = "Nachname, Vorname"
#let exam-duration = ("Dauer ", " Minuten.")
#let exam-weekdays = (
  "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag",
)
#let exam-months = (
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
)
#let exam-grade-words = ("Aufgabe", "Punkte", "Punktzahl", "Total:")
{% elif lang in ('it', 'italian', 'italiano') %}
#let exam-problem-label = "{{ problem_label or 'Problema' }}"
#let exam-point-words = ("punto", "punti")
#let exam-rules-label = "Istruzioni"
#let exam-next-page = "Vai alla pagina successiva..."
#let exam-page-of = ("Pagina ", " di ")
#let exam-name-label = "Cognome, Nome"
#let exam-duration = ("Durata ", " minuti.")
#let exam-weekdays = (
  "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica",
)
#let exam-months = (
  "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
  "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
)
#let exam-grade-words = ("Domanda", "Punti", "Punteggio", "Totale:")
{% else %}
#let exam-problem-label = "{{ problem_label or 'Problem' }}"
#let exam-point-words = ("point", "points")
#let exam-rules-label = "Instructions"
#let exam-next-page = "Go to the next page..."
#let exam-page-of = ("Page ", " of ")
#let exam-name-label = "Surname, First name"
#let exam-duration = ("Duration ", " minutes.")
#let exam-weekdays = (
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)
#let exam-months = (
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
)
#let exam-grade-words = ("Question", "Points", "Score", "Total:")
{% endif %}

// One reserved answer line, pitch included — exam.cls's \dottedlinefillheight.
#let exam-line-height = 18pt
#let exam-grid-step = 5mm

#let exam-q = counter("exam-question")
#let exam-p = counter("exam-part")
#let exam-sp = counter("exam-subpart")
#let exam-ssp = counter("exam-subsubpart")

// An ISO date in the long form of the document language; anything else, and
// any date that is not one, is printed as the author wrote it. No date at all
// falls back to the compile date, as `\today' does on the LaTeX side; it is
// spelled without the weekday, the form `\today' itself prints.
#let exam-long-date(raw) = {
  let written = raw.trim()
  if written == "" {
    let today = datetime.today()
    return [#today.day() #exam-months.at(today.month() - 1) #today.year()]
  }
  let parts = written.split("-")
  if parts.len() < 3 { return written }
  let day = parts.at(2).split("T").at(0).split(" ").at(0)
  if parts.at(0).len() != 4 or parts.at(1).len() != 2 or day.len() < 2 { return written }
  let stamp = datetime(year: int(parts.at(0)), month: int(parts.at(1)), day: int(day))
  [#exam-weekdays.at(stamp.weekday() - 1) #stamp.day() #exam-months.at(stamp.month() - 1) #stamp.year()]
}

// ---------------------------------------------------------------------------
// Page, text, headings
// ---------------------------------------------------------------------------

#set document(
  title: "{{ display_title | replace('"', '\\"') }}",
{% if author_names %}
  author: ({% for name in author_names %}"{{ name | replace('"', '\\"') }}", {% endfor %}),
{% endif %}
)
#set page(
  paper: "{{ (paper.get('format', 'a4') if paper is mapping else paper) or 'a4' }}",
  margin: exam-margin,
  header-ascent: 5.8mm,  // the running head 17.7 mm from the top, where exam.cls puts it
  footer-descent: 17mm,  // the foot 289 mm from the top, as in the LaTeX exam
  numbering: none,
  header: context {
    // The cover carries none, and a running head names the last question the
    // page reached — what \runningheader reads at shipout time.
    if here().page() == 1 { return }
    // The name field again on every recto — the even physical pages, as the
    // LaTeX template counts them at shipout — so a sheet handed in alone
    // still carries a name.
    if exam-recto-name and calc.even(here().page()) {
      place(top + right, dy: 5mm)[
        #strong[#exam-name-label :] #h(0.6em)
        #box(width: 62mm, height: 8mm, stroke: 0.5pt + black)
      ]
    }
    let reached = query(<exam-entry>).filter(it => (
      it.value.kind == "question" and it.location().page() <= here().page()
    ))
    block(width: 100%, text(size: 0.92em, grid(
      columns: (1fr, auto), align: (left + bottom, right + bottom),
      [{{ header_left | te }}],
      if reached.len() > 0 [#exam-problem-label #reached.len()] else [],
    )))
  },
  footer: context {
{% if not minimal %}
    if here().page() == 1 { return }
{% endif %}
    let number = counter(page).get().first()
    let total = counter(page).final().first()
    block(width: 100%, text(size: 0.92em, grid(
      columns: (1fr, auto, 1fr), align: (left + top, center + top, right + top),
      if exam-next-page-advice and number < total [#exam-next-page] else [],
      [#exam-page-of.at(0)#number#exam-page-of.at(1)#total],
      if here().page() == 1 and {{ 'true' if minimal else 'false' }} [] else [{{ course | te }}],
    )))
  },
)
#set text(font: "New Computer Modern", size: 10.5pt, lang: "{{ lang }}")
#set par(justify: true, leading: 0.62em, spacing: 1.05em)
// Questions carry their own numbering; a heading left in the text by
// `heading=true` is an ordinary one.
#set heading(numbering: none)
#show heading: set block(above: 1.4em, below: 0.7em)
{% if uses_eqnref %}
#set math.equation(numbering: "(1)")
{% endif %}

{{ prelude }}

// ---------------------------------------------------------------------------
// Contract functions (texsmith.typ), restyled for an exam. They belong after
// the prelude: a `#let` only reaches the calls below it.
// ---------------------------------------------------------------------------

// A thematic break turns the page. That is the contract's own reading, but an
// exam depends on it, so it says so.
#let ts-divider() = pagebreak(weak: true)

// A listing is a thin framed box with square corners, like the `tscode` box
// template.tex sets up. The rule is on `raw` rather than on `ts-code`: the
// writer names `#ts-code` only for a fence that carries a title, a caption or
// an id, and an exam's fences carry none.
#show raw.where(block: true): it => block(
  width: 100%, stroke: 0.5pt + black, radius: 2pt, inset: (x: 0.8em, y: 0.6em),
  above: 0.8em, below: 0.8em, breakable: true, it,
)
// An exam is printed in black and white, and the LaTeX side prints its
// listings in one colour: no syntax highlighting here either.
#set raw(theme: none)
#show raw: set text(size: 0.92em)

// …so `ts-code` adds the caption and lets the frame come from the rule above,
// which has already framed the fence inside it.
#let ts-code(
  title: none, linenums: none, hl-lines: (), id: none, caption: none, class: (), ..attrs
) = {
  let body = attrs.pos().at(0, default: [])
  let head = if title != none { title } else { caption }
  let listing = if head == none { body } else {
    block(above: 0.8em, below: 0.8em, breakable: true)[
      #block(below: 0.2em, strong(head))
      #body
    ]
  }
  if id != none [#listing #label(id)] else { listing }
}

// A task list the exam pass did not read as a multiple choice: a box to tick,
// never a ticked one — nothing on an exam is answered in advance.
#let ts-task(state, body) = [#box(
  width: 0.75em, height: 0.75em, stroke: 0.6pt + black, baseline: 0.05em,
) #body]

// ---------------------------------------------------------------------------
// The exam constructs, as `passes/typst.py` calls them
// ---------------------------------------------------------------------------

// A, B, … Z, AA, AB — the letters of the choices, as `choice_label` spells them.
#let exam-letter(index) = {
  let alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  let out = ""
  let value = index + 1
  while value > 0 {
    let rest = calc.rem(value - 1, 26)
    out = alphabet.slice(rest, rest + 1) + out
    value = calc.quo(value - 1, 26)
  }
  out
}

#let exam-points-note(points) = text(size: 0.95em)[(#points #exam-point-words.at(
  if points == "1" { 0 } else { 1 },
))]

// The points of a part, in the right margin — \pointsinrightmargin.
#let exam-margin-points(points) = box(width: 0pt, height: 0pt, context {
  let margin = ts-page-margin("right")
  place(
    top + left,
    dx: page.width - margin + 3mm - here().position().x,
    dy: -0.85em,
    block(width: margin - 6mm, text(size: 0.9em)[(#points)]),
  )
})

// The questions, each with the points of everything inside it — the sum
// \pointsofquestion reports and \gradetable prints.
#let exam-question-scores() = {
  let questions = ()
  for entry in query(<exam-entry>).map(it => it.value) {
    let score = if entry.points == none { 0.0 } else { float(entry.points) }
    if entry.kind == "question" {
      questions.push((title: entry.title, score: score))
    } else if questions.len() > 0 {
      questions.last().score += score
    }
  }
  questions
}

#let exam-question(points: none, id: none, body) = {
  exam-q.step()
  exam-p.update(0)
  exam-sp.update(0)
  exam-ssp.update(0)
  // What the grade table counts, read back with `query`.
  [#metadata((kind: "question", points: points, title: body)) <exam-entry>]
  if id != none [#metadata(none) #label(id)]
  block(width: 100%, above: 1.8em, below: 0.9em, context {
    // A question without points of its own is worth its parts, as
    // \pointsofquestion sums them for \titledquestion's own line.
    let index = exam-q.get().first()
    let shown = if points != none { points } else {
      let scores = exam-question-scores()
      let total = if index <= scores.len() { scores.at(index - 1).score } else { 0.0 }
      if total == 0 { none } else if calc.fract(total) == 0 { str(int(total)) } else { str(total) }
    }
    grid(
      columns: (1fr, auto), column-gutter: 1em, align: (left + bottom, right + bottom),
      strong[#exam-problem-label #index#if body != [] [ : #body]],
      if exam-points-enabled and shown != none { exam-points-note(shown) } else { [] },
    )
  })
}

// A part, a subpart, a subsubpart: a run-in label, then the text. There is no
// indentation to go with it — a Typst container refuses the page break a `---`
// or a `newpage=true` puts inside a question.
#let exam-level(level, nested, pattern, points, id, body) = {
  level.step()
  for inner in nested { inner.update(0) }
  // A part's points count towards its question's total, as \gradetable adds
  // \pointsofquestion over the whole question.
  if points != none [#metadata((kind: "part", points: points)) <exam-entry>]
  context strong[#numbering(pattern, level.get().first())]
  if id != none [#metadata(none) #label(id)]
  if exam-points-enabled and points != none { exam-margin-points(points) }
  h(0.4em)
  body
}

#let exam-part(points: none, id: none, body) = exam-level(
  exam-p, (exam-sp, exam-ssp), "(a)", points, id, body,
)
#let exam-subpart(points: none, id: none, body) = exam-level(
  exam-sp, (exam-ssp,), "i.", points, id, body,
)
#let exam-subsubpart(points: none, id: none, body) = exam-level(
  exam-ssp, (), "A)", points, id, body,
)

// `(a) ________`, flush right; the expected answer takes the rule's place on
// the answer key.
#let exam-answerline(answer: none) = {
  if exam-compact { return }
  block(width: 100%, above: 0.6em, below: 0.8em, align(right, context {
    let part = exam-p.get().first()
    let tag = if part > 0 [(#numbering("a", part))#h(0.6em)] else []
    if exam-solution-mode and answer != none {
      [#tag#box(width: 32mm, align(center, strong(answer)))]
    } else {
      [#tag#box(width: 32mm, height: 0.9em, stroke: (bottom: 0.5pt + black))]
    }
  }))
}

#let exam-fillin(width: 20mm, body) = {
  if exam-solution-mode {
    strong(body)
  } else if exam-fillin-style == "dotted" {
    box(width: width, baseline: 0.15em, repeat(gap: 2pt)[.])
  } else {
    box(width: width, height: 0.85em, stroke: (bottom: 0.5pt + black))
  }
}

// A multiple-choice list. The pass hands the choices over as a bullet list —
// the one shape a marker with no closing delimiter can make — so the letters,
// the columns and the answer line are decided here.
// The choices the pass wrapped in this call. Markup hands them over as bare
// `list.item`s among the whitespace — the enclosing `list` is only built when
// the content is laid out, which is what this call replaces.
#let exam-choice-items(body) = {
  if body.func() == list.item { return (body.body,) }
  if body.func() == list { return body.children.map(it => it.body) }
  let items = body
    .fields()
    .at("children", default: ())
    .filter(it => it.func() == list.item)
    .map(it => it.body)
  if items.len() > 0 { items } else { (body,) }
}

#let exam-choices(correct: (), body) = {
  let items = exam-choice-items(body)
  let widest = calc.max(0, ..items.map(it => ts-plain(it).len()))
  let wanted = if widest <= 16 { 4 } else if widest <= 28 { 3 } else if widest <= 46 { 2 } else { 1 }
  let entry(index, item) = {
    let marked = exam-solution-mode and index in correct
    let tag = if exam-choice-style == "checkbox" {
      if marked [#box(baseline: 0.05em)[☒]] else [#box(baseline: 0.05em)[☐]]
    } else [#exam-letter(index).]
    [#tag #h(0.3em) #if marked { strong(item) } else { item }]
  }
  // Down the first column, then the second — the reading order `columen` lays
  // the LaTeX choices out in. A grid fills row by row, so the cells are placed
  // in that order rather than the choices being reordered.
  let columns = calc.min(wanted, items.len())
  let rows = calc.ceil(items.len() / columns)
  let cells = range(rows * columns)
    .map(cell => {
      let index = calc.rem(cell, columns) * rows + calc.quo(cell, columns)
      if index < items.len() { entry(index, items.at(index)) } else { [] }
    })
  // 0.4em snugs the choices against the answer line that follows them; with
  // no answer line to follow — a compact document drops it — the next part
  // would butt straight up against the last choice, so the gap between two
  // parts is restored instead.
  block(width: 100%, above: 0.7em, below: if exam-compact { 1.05em } else { 0.4em },
    pad(left: 1.2em, grid(
      columns: (1fr,) * columns, column-gutter: 1em, row-gutter: 0.45em, ..cells,
    )))
  exam-answerline(answer: if correct.len() > 0 {
    correct.map(exam-letter).join(", ")
  } else { none })
}

// -- the space the answer is written in --------------------------------------

// One line, the rule sitting at the bottom of its own slot, so a run of them
// is exactly `count * exam-line-height` high.
#let exam-rule-line() = box(width: 100%, height: exam-line-height, align(bottom, {
  if exam-text-style == "lines" {
    line(length: 100%, stroke: 0.5pt + black)
  } else {
    box(width: 100%, repeat(gap: 3pt)[.])
  }
}))

#let exam-line-count(value) = if type(value) == int {
  value
} else {
  calc.max(1, int(value / exam-line-height))
}

#let exam-lines(count) = block(
  width: 100%, above: 1em, below: 1em,
  stack(dir: ttb, ..range(count).map(_ => exam-rule-line())),
)

#let exam-empty-box(width, height) = {
  let framed = block(
    width: if width == auto { 100% } else { width },
    height: if height == auto { 40mm } else { height },
    stroke: 0.5pt + black,
  )
  block(above: 1em, below: 1em, width: 100%, if width == auto {
    framed
  } else {
    align(center, framed)
  })
}

#let exam-grid-area(rows) = block(above: 1em, below: 1em, layout(size => {
  let columns = int(size.width / exam-grid-step)
  let stroke = 0.3pt + luma(160)
  box(width: columns * exam-grid-step, height: rows * exam-grid-step, {
    for index in range(columns + 1) {
      place(top + left, dx: index * exam-grid-step, line(
        end: (0pt, rows * exam-grid-step), stroke: stroke,
      ))
    }
    for index in range(rows + 1) {
      place(top + left, dy: index * exam-grid-step, line(
        end: (columns * exam-grid-step, 0pt), stroke: stroke,
      ))
    }
  })
}))

// `lines=fill`: reserved lines down to the bottom of the page.
#let exam-fill-page() = context {
  // The room left on this page, less the block's own 1em above and a line of
  // slack: one line too many and the whole run moves to the next page.
  let slack = (1.2em).to-absolute()
  let available = page.height - ts-page-margin("bottom") - here().position().y - slack
  let count = int(available / exam-line-height)
  if count > 0 { exam-lines(count) }
}

#let exam-reserve(lines: none, grid: none, area: none) = {
  if exam-compact or exam-solution-mode { return }
  if area != none {
    exam-empty-box(..area)
  } else if grid != none {
    exam-grid-area(exam-line-count(grid))
  } else if lines == "fill" {
    exam-fill-page()
  } else if lines != none and exam-text-style == "box" {
    exam-empty-box(auto, exam-line-count(lines) * exam-line-height)
  } else if lines != none {
    exam-lines(exam-line-count(lines))
  }
}

// The answer, behind a thick rule — the `examanswerbar` of template.tex.
#let exam-solution(lines: none, grid: none, area: none, body) = {
  if exam-solution-mode {
    block(
      width: 100%, above: 1em, below: 1em, breakable: true,
      stroke: (left: 2pt + black), inset: (left: 0.7em, y: 0.2em), body,
    )
  } else {
    exam-reserve(lines: lines, grid: grid, area: area)
  }
}

// ---------------------------------------------------------------------------
// The cover page
// ---------------------------------------------------------------------------

{% if not logo_off %}
{# The same two sizes template.tex resolves: a `minimal' title page puts the
   logo beside the title block, where the cover size would reach the header
   rule, so it is the smaller of the two. #}
#let exam-logo-height = {{ '14.5mm' if minimal else '18mm' }}
{% if logo_file %}
#let exam-logo = image("{{ asset(logo_file) }}", height: exam-logo-height)
{% else %}
{% include "template/logos/heiglogo-" ~ vintage ~ ".typ" %}
#let exam-logo = image(
  bytes({{ 'heig-logo-color' if logo_color else 'heig-logo-mono' }}),
  format: "svg",
  height: exam-logo-height,
)
{% endif %}
{% endif %}

#let exam-name-field = [
  #strong[#exam-name-label :]
  #h(0.6em)
  #box(width: 62mm, height: 8mm, stroke: 0.5pt + black)
]


#let exam-grade-table() = context {
  let questions = exam-question-scores()
  if questions.len() == 0 { return }
  let shown(value) = if calc.fract(value) == 0 { str(int(value)) } else { str(value) }
  let cell(body) = grid.cell(inset: (x: 0.8em, y: 0.35em), body)
  align(center, grid(
    columns: (auto, auto, 18mm),
    stroke: 0.5pt + black,
    align: center + horizon,
    cell(strong(exam-grade-words.at(0))),
    cell(strong(exam-grade-words.at(1))),
    cell(strong(exam-grade-words.at(2))),
    ..questions
      .enumerate()
      .map(((index, entry)) => (
        cell(if entry.title == [] [#exam-problem-label #(index + 1)] else { entry.title }),
        cell(if entry.score == 0 [] else [#shown(entry.score)]),
        cell([]),
      ))
      .flatten(),
    cell(strong(exam-grade-words.at(3))),
    cell(strong(shown(questions.map(it => it.score).sum(default: 0.0)))),
    cell([]),
  ))
}

{% if rules %}
#let exam-rules-box() = block(
  width: 100%, stroke: 1pt + black, inset: (x: 1em, y: 0.8em),
)[
  #strong[#exam-rules-label :]
  #v(0.5em)
  #set par(justify: false)
  #set list(marker: [—], indent: 0.4em, spacing: 0.55em)
{% if duration %}
  - #exam-duration.at(0){{ duration | te }}#exam-duration.at(1)
{% endif %}
{% for rule in rules %}
  - {{ rule }}
{% endfor %}
]
{% endif %}

{% if minimal %}
{# `titlepage: minimal` — a title block at the top of page 1, no cover. #}
{% if not logo_off %}
#place(top + left, dx: -exam-margin.left + 24mm, dy: -exam-margin.top + 10mm, exam-logo)
{% endif %}
{# Page 1 carries no running head: take back the room the margin reserves for
   one, so the title starts at the top of the text block. #}
#v(-exam-head-room)
#align(center)[
{% if solution %}
  #text(fill: red, weight: "bold")[Solution]

{% endif %}
  #text(size: 1.6em, weight: "bold")[{{ display_title | te }}]
{% if subtitle %}

  #emph[{{ subtitle | te }}]
{% endif %}
{% for block in author_blocks %}

  {{ block }}
{% endfor %}
]
{# The two rules, the course line and the school line are one unit. Block
   spacing is set inside it, so the document's paragraph spacing does not prise
   the rules apart; `above'/`below' alone hold it off the title and the body. #}
#block(width: 100%, above: 0.7em, below: 0.9em)[
  #set block(spacing: 0.3em)
  #line(length: 100%, stroke: 0.5pt + black)
  #grid(columns: (1fr, auto), align: (left + horizon, right + horizon),
    text(size: 1.05em)[{{ course | te }}],
    text(size: 1.05em)[#exam-long-date("{{ exam_date }}"){% if version %}, {{ version | te }}{% endif %}],
  )
{% if school or department %}
  #align(center, emph[{{ school | te }}{% if school and department %} — {% endif %}{{ department | te }}])
{% endif %}
  #line(length: 100%, stroke: 0.5pt + black)
]
{% else %}
{# `titlepage: cover` — the LaTeX `coverpages`. #}
{% if not logo_off %}
#place(top + left, dx: -exam-margin.left + 10mm, dy: -exam-margin.top + 10mm, exam-logo)
{% endif %}
#place(top + right, dy: -exam-margin.top + 18mm, exam-name-field)
#v(26mm)
#align(center)[
  #text(size: 2.2em, weight: "bold")[{{ display_title | te }}]
{% if subtitle %}

  #emph[{{ subtitle | te }}]
{% endif %}
{% if department %}

  #emph[{{ department | te }}]
{% endif %}
]
#v(1fr)
#align(center)[
{% if solution %}
  #text(size: 1.2em, fill: red, weight: "bold")[SOLUTION]

{% endif %}
  #text(size: 1.15em)[#exam-long-date("{{ exam_date }}"){% if version %}, {{ version | te }}{% endif %}]
{% for block in author_blocks %}

  {{ block }}
{% endfor %}
]
#v(1.5em)
{% if points %}
#exam-grade-table()
{% endif %}
#v(1fr)
{% if rules %}
#exam-rules-box()
{% endif %}
#pagebreak()
#counter(page).update(1)
{% endif %}

{{ body }}

{% if acronyms %}
#v(1em)
{{ acronyms }}
{% endif %}
{% if has_index %}
#ts-print-index()
{% endif %}
{% if has_bibliography %}
#bibliography({{ bibliography_sources }}, style: "ieee")
{% endif %}

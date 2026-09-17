"""The ``exam`` IR pass: read the exam constructs, hand them to a backend emitter.

Declared by the template manifest (``[latex.template] passes``), so it applies
only while the exam template renders. It runs last among the ``pre`` passes:
``include`` has spliced the included sources, ``var`` expanded the moustaches,
``assets`` copied the images of a solution, ``emoji`` and ``scripts`` have
rewritten the inline runs the pass then writes out.

What it recognises, and what it leaves alone:

``Header``
    the question structure. The depth is the heading level normalised against
    the shallowest heading of the document (the ``headings`` pass's
    ``base_level`` rule), and the ``questions``/``parts``/``subparts``/
    ``subsubparts`` environments of ``exam.cls`` are opened and closed around
    it by a small state machine. ``points=``, ``answer=`` and ``heading=`` are
    heading attributes; ``heading=true`` leaves the machinery and renders an
    ordinary heading, and ``newpage=true`` starts the question on a fresh
    page (what a ``---`` before it would say, which a *first* line cannot: a
    leading ``---`` opens the front matter).
``BulletList`` whose items carry a task marker
    a multiple-choice question: ``- [x]`` is the correct choice, and the
    letters of the correct ones are computed here for the answer line.
``Div{name="solution"}``
    the answer, and the space reserved for it in exam mode (``lines``,
    ``grid``, ``box``, ``newpage``). The body stays IR so the ``highlight``
    post-pass still sees the code blocks inside it; only the wrappers are raw.
    ``::: div {.solution}`` and a ``solution`` declared under
    ``press.declare.admonitions`` are read the same way: those two spellings
    are in tmark's container registry, so they parse without the
    ``container-unknown`` warning ``::: solution`` draws — a *parse* finding,
    emitted before any pass runs, which is why no pass can take it back.
``SpanNode`` with ``w=`` / ``width=`` / ``char-width-scale=`` or a ``fillin`` class
    an inline blank, ``[answer]{w=3cm}``. A bare ``[answer]`` left in the text
    by the parser is one too, unless ``exam.fillin-bare`` is false.

Everything else — callouts, code fences, tables, raw blocks, thematic breaks —
is tmark's, rendered through the contract macros the template redefines.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import TYPE_CHECKING

from texsmith.passes import PassContext, spec
from tmark.ir import model
from tmark.ir.walk import map_inlines, map_tree

from texsmith_template_exam.exam.utils import (
    is_empty_title,
    normalize_answer_text,
    normalize_fillin_width,
    normalize_points,
)
from texsmith_template_exam.passes import latex as latex_backend
from texsmith_template_exam.passes.model import (
    Choice,
    ChoiceGroup,
    Emitter,
    FillIn,
    Question,
    Solution,
)
from texsmith_template_exam.passes.options import ExamOptions, coerce_bool, coerce_scale
from texsmith_template_exam.passes.render import plain_text


if TYPE_CHECKING:  # pragma: no cover - typing only
    from texsmith.core.documents import Document


#: Titles that mean "this question has no name".
_DASH_TITLES = frozenset({"-", "\N{EN DASH}", "\N{EM DASH}"})
#: Keys marking a ``Span`` as an inline blank.
_WIDTH_KEYS = ("w", "width")
_SCALE_KEYS = ("char-width-scale", "char_width_scale", "scale")
_FILLIN_CLASSES = frozenset({"fillin", "blank"})
#: A bare ``[answer]`` left in the text by the parser.
_BARE_FILLIN = re.compile(r"\[([^\]\n]+)\]")
#: The emitters, by backend. A Typst twin registers itself here.
_EMITTERS = {"latex": latex_backend.LatexEmitter}


def _kv(attrs: model.Attrs, key: str) -> str | None:
    for name, value in attrs.kv:
        if name == key:
            return value
    return None


def _first_kv(attrs: model.Attrs, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _kv(attrs, key)
        if value is not None:
            return value
    return None


def _slugify(text: str) -> str | None:
    try:
        from slugify import slugify
    except ImportError:  # pragma: no cover - python-slugify ships with texsmith
        return None
    return slugify(text, separator="-") or None


# -- fill-in blanks --------------------------------------------------------


def _as_fillin(node: model.SpanNode) -> FillIn | None:
    """``node`` read as an inline blank, ``None`` when it is an ordinary span."""
    width_raw = _first_kv(node.attrs, _WIDTH_KEYS)
    scale_raw = _first_kv(node.attrs, _SCALE_KEYS)
    classed = bool(_FILLIN_CLASSES.intersection(node.attrs.classes))
    if width_raw is None and scale_raw is None and not classed:
        return None
    width = normalize_fillin_width(width_raw) if width_raw else None
    scale = coerce_scale(scale_raw, default=0.0) if scale_raw else None
    return FillIn(
        answer=node.content,
        plain=plain_text(node.content),
        width=width or None,
        scale=scale or None,
    )


# -- multiple choice -------------------------------------------------------


def _has_nested_list(blocks: tuple[model.Block, ...]) -> bool:
    return any(isinstance(block, (model.BulletList, model.OrderedList)) for block in blocks)


def _as_choice_group(node: model.Block) -> ChoiceGroup | None:
    """``node`` read as a multiple-choice list, ``None`` otherwise."""
    if not isinstance(node, model.BulletList):
        return None
    if not any(item.task is not None for item in node.items):
        return None
    if any(_has_nested_list(item.content) for item in node.items):
        return None
    return ChoiceGroup(
        choices=tuple(
            Choice(correct=getattr(item.task, "value", item.task) == "done", body=item.content)
            for item in node.items
        )
    )


# -- solutions -------------------------------------------------------------


def _as_solution(node: model.Block) -> Solution | None:
    """``node`` read as a solution block, whichever way the author spelled it.

    ``::: solution`` is the spelling the corpus uses; tmark's container
    registry does not know the name, so it warns and the pass claims it (and
    drops the warning). ``::: div {.solution}`` is the spelling 0.8 documents
    for a container a template styles, and a ``solution`` declared under
    ``press.declare.admonitions`` arrives as an ``Admonition`` — both are
    accepted so a corpus can move to either without the template changing.
    """
    if isinstance(node, model.Div):
        if node.name != "solution" and not (
            node.name == "div" and "solution" in node.attrs.classes
        ):
            return None
        attrs, content = node.attrs, node.content
    elif isinstance(node, model.Admonition) and node.kind == "solution":
        attrs, content = node.attrs, node.content
    else:
        return None
    return Solution(
        lines=_kv(attrs, "lines"),
        grid=_kv(attrs, "grid"),
        box=_kv(attrs, "box"),
        newpage=coerce_bool(_kv(attrs, "newpage"), default=False),
        content=content,
    )


# -- the question structure ------------------------------------------------


class _Structure:
    """Which ``exam.cls`` list environments are open, and what a depth change costs."""

    __slots__ = ("open",)

    def __init__(self) -> None:
        #: The environments currently open, outermost first.
        self.open: list[str] = []

    def enter(self, depth: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """The environments to close and to open before a heading of ``depth``.

        A question (depth 1) closes everything; a part needs ``parts`` open and
        nothing deeper; a subpart needs ``parts`` and ``subparts``.
        """
        wanted = latex_backend.LEVEL_ENVIRONMENTS[: max(0, depth - 1)]
        closed = tuple(reversed(self.open[len(wanted) :]))
        del self.open[len(wanted) :]
        opened = tuple(wanted[len(self.open) :])
        self.open.extend(opened)
        return opened, closed

    def close_all(self) -> tuple[str, ...]:
        closed = tuple(reversed(self.open))
        self.open.clear()
        return closed


_NO_SPAN = model.Span(file=0, start=0, end=0)


def _joinable(block: model.Block) -> bool:
    """A block a question label can share its paragraph with.

    Prose, and only prose. A paragraph holding one image alone is a *figure* to
    the writer, and gluing a label in front of it would turn it into an inline
    picture; a paragraph opening with ``[`` would have its first bracket read as
    the optional points argument of ``\\part``.
    """
    if not isinstance(block, (model.Para, model.Plain)):
        return False
    if _is_lone_image(block.content):
        return False
    return not plain_text(block.content).lstrip().startswith("[")


def _is_lone_image(content: tuple[model.Inline, ...]) -> bool:
    """A paragraph that is one image and nothing else (the writer's figure)."""
    meaningful = [
        node for node in content if not isinstance(node, (model.Space, model.SoftBreak))
    ]
    return len(meaningful) == 1 and isinstance(meaningful[0], model.Image)


def _heading_depths(blocks: tuple[model.Block, ...]) -> int:
    """The shallowest top-level heading level, ``1`` when the document has none."""
    levels = [block.level for block in blocks if isinstance(block, model.Header)]
    return min(levels) if levels else 1


@dataclass(slots=True)
class _Rewriter:
    """The whole rewrite of one document's block list."""

    ctx: PassContext
    options: ExamOptions
    emitter: Emitter

    def raw_block(self, text: str, span: model.Span) -> model.RawBlock:
        return model.RawBlock(
            format=self.emitter.raw_format, text=text, id=self.ctx.ids.next(), span=span
        )

    def raw_inline(self, text: str, span: model.Span) -> model.RawInline:
        return model.RawInline(
            format=self.emitter.raw_format, text=text, id=self.ctx.ids.next(), span=span
        )

    def framed(
        self, frame: tuple[str, str], content: tuple[model.Inline, ...], span: model.Span
    ) -> tuple[model.Inline, ...]:
        """``content`` between the two halves of ``frame``, empty halves dropped."""
        head, tail = frame
        parts: list[model.Inline] = []
        if head:
            parts.append(self.raw_inline(head, span))
        parts.extend(content)
        if tail:
            parts.append(self.raw_inline(tail, span))
        return tuple(parts)

    # Inline blanks, everywhere in the tree (tables and callouts included).

    def rewrite_fillins(self, root: model.Document) -> model.Document:
        def visit(node: model.Node) -> model.Node:
            if not isinstance(node, model.SpanNode):
                return node
            blank = _as_fillin(node)
            if blank is None:
                return node
            return model.SpanNode(
                attrs=model.Attrs(),
                content=self.framed(self.emitter.fillin(blank), node.content, node.span),
                id=node.id,
                span=node.span,
            )

        # The bare brackets go first, fenced off from the blanks that already
        # carry an attribute group: an escaped ``[\[D\]]{w=6cm}`` answer is a
        # literal pair of brackets, not a blank inside a blank.
        if self.options.bare_fillin:
            root = self.rewrite_bare_fillins(root)
        return map_tree(root, visit)

    def rewrite_bare_fillins(self, root: model.Document) -> model.Document:
        """``[answer]`` in prose, with no attribute group, is a blank too.

        tmark has no syntax for it — a bracketed run that is not a link, a
        span or a reference stays literal text — but it is how the corpus and
        the demo were written, so the pass splits the text nodes itself.
        Content that is not prose (code, math, a link target) never reaches a
        ``Str``, and a span that already carries an attribute group is fenced
        off, so only the leftovers are seen here.
        """

        def split(node: model.Inline) -> model.Inline | tuple[model.Inline, ...]:
            if not isinstance(node, model.Str) or "[" not in node.text:
                return node
            parts: list[model.Inline] = []
            cursor = 0
            for match in _BARE_FILLIN.finditer(node.text):
                if match.start() > cursor:
                    parts.append(self._text(node.text[cursor : match.start()], node.span))
                answer = (self._text(match.group(1), node.span),)
                blank = FillIn(answer=answer, plain=match.group(1), width=None)
                parts.extend(self.framed(self.emitter.fillin(blank), answer, node.span))
                cursor = match.end()
            if not parts:
                return node
            if cursor < len(node.text):
                parts.append(self._text(node.text[cursor:], node.span))
            return tuple(parts)

        def is_blank(node: model.Node) -> bool:
            return isinstance(node, model.SpanNode) and _as_fillin(node) is not None

        return map_inlines(root, split, skip=is_blank)

    def _text(self, text: str, span: model.Span) -> model.Str:
        return model.Str(text=text, id=self.ctx.ids.next(), span=span)

    # The block structure.

    def rewrite_blocks(
        self, blocks: tuple[model.Block, ...], *, top_level: bool
    ) -> tuple[model.Block, ...]:
        structure = _Structure()
        base = _heading_depths(blocks) if top_level else 1
        out: list[model.Block] = []
        #: A question label waiting to be glued to the text that follows it:
        #: ``\part`` and its question must share a paragraph, or the blank line
        #: between two blocks opens an empty one under the label.
        pending_label: tuple[model.Inline, ...] = ()
        pending_answerline: tuple[model.Inline, ...] = ()
        plain_mode_level: int | None = None

        for block in blocks:
            if top_level and isinstance(block, model.Header):
                if pending_label:
                    out.append(model.Plain(content=pending_label, id=self.ctx.ids.next(),
                                           span=block.span))
                    pending_label = ()
                pending_label, pending_answerline = self._header(
                    block, base, structure, out, plain_mode_level
                )
                plain_mode_level = self._plain_mode(block, base, plain_mode_level)
                continue

            rewritten = self.rewrite_block(block)
            if pending_label:
                head, *rest = rewritten
                if _joinable(head):
                    glue = (*pending_label, self.raw_inline("\n", head.span))
                    rewritten = (replace(head, content=(*glue, *head.content)), *rest)
                else:
                    out.append(
                        model.Plain(
                            content=pending_label, id=self.ctx.ids.next(), span=block.span
                        )
                    )
                pending_label = ()

            if pending_answerline and self._is_text(block):
                out.extend(rewritten)
                out.append(
                    model.Plain(
                        content=pending_answerline, id=self.ctx.ids.next(), span=block.span
                    )
                )
                pending_answerline = ()
                continue
            out.extend(rewritten)

        span = blocks[-1].span if blocks else _NO_SPAN
        for leftover in (pending_label, pending_answerline):
            if leftover:
                out.append(
                    model.Plain(content=leftover, id=self.ctx.ids.next(), span=span)
                )
        if top_level:
            closed = structure.close_all()
            if closed:
                out.append(self.raw_block(self.emitter.close_levels(closed), span))
        return tuple(out)

    def rewrite_block(self, block: model.Block) -> tuple[model.Block, ...]:
        """One block, possibly expanded into several."""
        solution = _as_solution(block)
        if solution is not None:
            return self._solution(solution, block.span)

        group = _as_choice_group(block)
        if group is not None:
            return (self._choices(group, block.span),)

        if isinstance(block, (model.Div, model.BlockQuote, model.Admonition, model.Figure)):
            content = self.rewrite_blocks(block.content, top_level=False)
            if content != block.content:
                return (replace(block, content=content),)
        elif isinstance(block, (model.BulletList, model.OrderedList)):
            items = tuple(
                replace(item, content=self.rewrite_blocks(item.content, top_level=False))
                for item in block.items
            )
            if items != block.items:
                return (replace(block, items=items),)
        return (block,)

    def _choices(self, group: ChoiceGroup, span: model.Span) -> model.Block:
        """One ``Plain`` block: the list markup with the choice bodies still IR."""
        head, tail = self.emitter.choices_frame(group)
        separator = self.emitter.separator
        parts: list[model.Inline] = [self.raw_inline(head, span)]
        for choice in group.choices:
            marker = f"{separator}{self.emitter.choice_marker(choice)} "
            parts.append(self.raw_inline(marker, span))
            parts.extend(_item_inlines(choice.body))
        parts.append(self.raw_inline(separator + tail, span))
        return model.Plain(content=tuple(parts), id=self.ctx.ids.next(), span=span)

    def _solution(self, solution: Solution, span: model.Span) -> tuple[model.Block, ...]:
        begin, end = self.emitter.solution(solution)
        content = self.rewrite_blocks(solution.content, top_level=False)
        blocks: list[model.Block] = []
        if begin:
            blocks.append(self.raw_block(begin, span))
        blocks.extend(content)
        if end:
            blocks.append(self.raw_block(end, span))
        return tuple(blocks)

    # Headings.

    def _plain_mode(self, header: model.Header, base: int, current: int | None) -> int | None:
        level = header.level - base + 1
        if coerce_bool(_kv(header.attrs, "heading"), default=False):
            return level
        if current is not None and level <= current:
            return None
        return current

    def _header(
        self,
        header: model.Header,
        base: int,
        structure: _Structure,
        out: list[model.Block],
        plain_mode_level: int | None,
    ) -> tuple[tuple[model.Inline, ...], tuple[model.Inline, ...]]:
        """Emit one heading; return ``(label to glue, answer line to defer)``."""
        depth = header.level - base + 1
        title = plain_text(header.content)
        anonymous = is_empty_title(title)
        points = normalize_points(_kv(header.attrs, "points")) if self.options.points else None
        answer = normalize_answer_text(_kv(header.attrs, "answer"))
        explicit_plain = coerce_bool(_kv(header.attrs, "heading"), default=False)
        nested_plain = plain_mode_level is not None and depth > plain_mode_level
        answerline: tuple[model.Inline, ...] = ()
        if answer and not self.options.compact:
            answerline = self.framed(
                self.emitter.answerline_frame(), _answer_inlines(answer), header.span
            )

        if explicit_plain or nested_plain or not (1 <= depth <= 4):
            closed = structure.close_all()
            out.append(self.raw_block(self.emitter.plain_heading(closed), header.span))
            out.append(replace(header, level=min(max(depth, 1), 6)))
            if answerline:
                out.append(
                    model.Plain(content=answerline, id=self.ctx.ids.next(), span=header.span)
                )
            return (), ()

        opened, closed = structure.enter(depth)
        question = Question(
            depth=depth,
            title=header.content,
            anonymous=anonymous,
            points=points,
            ref=header.attrs.id or (None if anonymous else _slugify(title)),
            answer=answer,
            newpage=coerce_bool(_kv(header.attrs, "newpage"), default=False),
        )
        frame = self.emitter.question(question, opened, closed)
        content = () if anonymous else header.content
        label = self.framed(frame, content, header.span)
        if not answerline:
            return label, ()
        if title.strip() in _DASH_TITLES:
            # An anonymous question: the answer line belongs after the text that
            # follows it, not squeezed between the label and the question.
            return label, answerline
        out.append(model.Plain(content=label, id=self.ctx.ids.next(), span=header.span))
        out.append(model.Plain(content=answerline, id=self.ctx.ids.next(), span=header.span))
        return (), ()

    @staticmethod
    def _is_text(block: model.Block) -> bool:
        return isinstance(block, (model.Para, model.Plain)) and bool(
            plain_text(block.content).strip()
        )


def _item_inlines(blocks: tuple[model.Block, ...]) -> tuple[model.Inline, ...]:
    """A choice body as inlines: a choice is one short paragraph."""
    if len(blocks) == 1 and isinstance(blocks[0], (model.Para, model.Plain)):
        return blocks[0].content
    return tuple(
        node
        for block in blocks
        if isinstance(block, (model.Para, model.Plain))
        for node in block.content
    )


def _answer_inlines(text: str) -> tuple[model.Inline, ...]:
    """A short attribute value (``answer=…``) parsed as inline Markdown."""
    from texsmith.readers.tmark import parse_payload
    from tmark.ir import codec

    blocks = codec.decode_document(parse_payload(text, name="<exam attribute>")).blocks
    if len(blocks) == 1 and isinstance(blocks[0], (model.Para, model.Plain)):
        return blocks[0].content
    return ()


@spec(
    "exam",
    stage="pre",
    after=("include", "var", "title", "epigraph", "snippet", "assets", "doi", "emoji", "scripts"),
)
def run(document: Document, ctx: PassContext) -> Document:
    """Rewrite the exam constructs of ``document`` for ``ctx.backend``."""
    ir = document.ir
    if ir is None:
        return document
    emitter_class = _EMITTERS.get(ctx.backend)
    if emitter_class is None:
        return document

    options = ExamOptions.from_context(ctx)
    rewriter = _Rewriter(ctx=ctx, options=options, emitter=emitter_class(options))
    with_blanks = rewriter.rewrite_fillins(ir)
    blocks = rewriter.rewrite_blocks(with_blanks.blocks, top_level=True)
    if blocks == ir.blocks:
        return document
    return document.evolve(ir=replace(with_blanks, blocks=blocks))


__all__ = ["run"]

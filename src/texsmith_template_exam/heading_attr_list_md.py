"""Extract heading attribute lists before inline processing.

Python-Markdown applies inline patterns (tree-processor priority ``20``) before
the stock ``attr_list`` tree-processor (priority ``8``).  TeXSmith registers a
smart-quote inline processor that rewrites straight double quotes (``"…"``)
into ``<q>`` elements, so a heading attribute list such as::

    ## `printf("%d", a[1])` { points=1 answer="20" }

is turned into ``{ points=1 answer=<q>20</q> }`` *before* ``attr_list`` ever
sees it.  ``attr_list`` then fails to match the (now split) block, the braces
are left as literal heading text, and ``points`` / ``answer`` / ``id`` silently
disappear.

This extension re-uses ``attr_list``'s own parser to consume the trailing
``{…}`` block on headings *before* inline processing runs, while the text is
still pristine.  The stock ``attr_list`` pass then finds nothing left to do, so
both passes stay consistent and every attribute-list spelling that ``attr_list``
already supports (``#id``, ``.class``, ``key=value``, ``key="quoted value"`` …)
keeps working regardless of the quoting style.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element

from markdown import Markdown
from markdown.extensions import Extension
from markdown.extensions.attr_list import AttrListTreeprocessor, isheader


# Run just above the inline tree-processor (priority ``20``) so the heading
# attribute block is read from the original text rather than from the
# inline-rewritten tree.
_PRIORITY = 21


class _HeadingAttrListTreeprocessor(AttrListTreeprocessor):
    """Consume trailing ``{…}`` attribute lists on headings early."""

    def run(self, doc: Element) -> None:  # type: ignore[override]
        for elem in doc.iter():
            if not isheader(elem) or not elem.text:
                continue
            # Before inline processing an ATX heading has no children: the whole
            # raw line lives in ``elem.text``.  If it already has children some
            # other processor ran first; leave it for the stock ``attr_list``.
            if len(elem):
                continue
            match = self.HEADER_RE.search(elem.text)
            if match is None:
                continue
            # ``strict=True`` mirrors stock ``attr_list``: when the block is not
            # a clean attribute list, nothing is assigned and the text is left
            # untouched (a non-empty remainder is returned).
            if not self.assign_attrs(elem, match.group(1), strict=True):
                elem.text = elem.text[: match.start()].rstrip("#").rstrip()


class HeadingAttrListExtension(Extension):
    """Register early heading attribute extraction for exam documents."""

    def extendMarkdown(self, md: Markdown) -> None:  # type: ignore[override]  # noqa: N802
        md.treeprocessors.register(
            _HeadingAttrListTreeprocessor(md),
            "texsmith_exam_heading_attr_list",
            priority=_PRIORITY,
        )


def makeExtension(**kwargs: object) -> HeadingAttrListExtension:  # noqa: N802
    return HeadingAttrListExtension(**kwargs)


__all__ = ["HeadingAttrListExtension", "makeExtension"]

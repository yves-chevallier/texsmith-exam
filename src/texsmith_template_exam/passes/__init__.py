"""The IR passes of the exam template.

``manifest.toml`` declares ``passes = ["texsmith_template_exam.passes.exam:run"]``
under ``[latex.template]`` (and will under ``[typst.template]``), so the rewrite
runs only while the exam template renders.

* :mod:`~texsmith_template_exam.passes.exam` — the pass: it reads the IR and
  describes what it found, backend-neutrally.
* :mod:`~texsmith_template_exam.passes.model` — those descriptions, and the
  ``Emitter`` protocol a backend implements.
* :mod:`~texsmith_template_exam.passes.latex` — the ``exam.cls`` emitter.
* :mod:`~texsmith_template_exam.passes.options` — the flags read from the
  ``PassContext`` (solution mode, compact mode, points, styles).
* :mod:`~texsmith_template_exam.passes.render` — IR to markup through
  ``tmark.write``, for the slices the emitters inline.
"""

from __future__ import annotations


__all__: list[str] = []

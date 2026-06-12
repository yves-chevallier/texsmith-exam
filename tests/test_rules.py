from __future__ import annotations

import pytest

from texsmith_template_exam.rules import resolve_attribute, resolve_rules


def test_preset_with_standard_expands_in_order() -> None:
    rules = resolve_rules({"preset": "exam", "standard": "c17"})
    assert rules[0] == "Écrire votre **nom** et votre **prénom** sur la première page."
    assert "Rendre toutes les feuilles de cet examen." in rules
    assert rules[-1].endswith("ISO/IEC 9899:2018.")


def test_te_and_exam_presets_differ_on_handin() -> None:
    te = resolve_rules({"preset": "te"})
    exam = resolve_rules({"preset": "exam"})
    assert "Rendre toutes les feuilles de ce travail écrit." in te
    assert "Rendre toutes les feuilles de cet examen." in exam


def test_prepend_and_append() -> None:
    rules = resolve_rules(
        {"prepend": ["replace-te1"], "preset": "te", "standard": "c17", "append": ["no-docs"]}
    )
    assert rules[0].startswith("Si vous rendez votre travail")
    assert rules[-1].startswith("Aucune consultation de documents")


def test_token_list_resolves_known_tokens() -> None:
    rules = resolve_rules(["name", "legible", "c17"])
    assert rules == [
        "Écrire votre **nom** et votre **prénom** sur la première page.",
        "Écrire **lisiblement**, au stylo ou au crayon à papier gras.",
        "Toutes les réponses concernent le langage C et son standard ISO/IEC 9899:2018.",
    ]


def test_unknown_token_is_literal_passthrough() -> None:
    assert resolve_rules(["Une consigne ad-hoc."]) == ["Une consigne ad-hoc."]
    # Mixed tokens and literals
    mixed = resolve_rules(["name", "Consigne maison."])
    assert mixed[1] == "Consigne maison."


def test_string_value_is_wrapped() -> None:
    assert resolve_rules("no-comm") == ["Aucun moyen de communication autorisé."]


def test_empty_and_none() -> None:
    assert resolve_rules([]) == []
    assert resolve_rules(None) == []


def test_unknown_preset_raises() -> None:
    with pytest.raises(ValueError, match="Unknown exam rules preset"):
        resolve_rules({"preset": "does-not-exist"})


def test_resolve_attribute_contract() -> None:
    # falls back when the resolved list is empty
    assert resolve_attribute([], None, ["fallback"]) == ["fallback"]
    # expands a preset mapping
    out = resolve_attribute({"preset": "te", "standard": "c11"}, None, [])
    assert out[-1].endswith("ISO/IEC 9899:2011.")


def test_manifest_references_resolve_attribute_by_import() -> None:
    """The manifest points at the callable; TeXSmith resolves it by import."""
    from texsmith.core.templates.manifest import _resolve_attribute_normaliser

    func = _resolve_attribute_normaliser("texsmith_template_exam.rules:resolve_attribute")
    assert func is resolve_attribute
    assert func({"preset": "exam"}, None, [])[0].startswith("Écrire votre")

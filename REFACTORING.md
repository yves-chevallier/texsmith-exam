# Refactoring Plan (Exam Template)

## Phase 0 — Baseline et sécurité
- [ ] Vérifier l’état des tests existants pour établir un baseline.
- [ ] Lister les points de couplage avec `texsmith` (API internes et publiques) à préserver.

## Phase 1 — Extraction d’utilitaires purs (sans changement de comportement)
- [x] Extraire les helpers de normalisation (truthy, parsing attrs, normalise values) vers `src/texsmith_template_exam/exam/utils.py`.
- [x] Remplacer les usages dispersés par les helpers centralisés.
- [ ] Valider que les tests existants passent.

## Phase 2 — Centralisation de la logique Fill-in
- [x] Créer `src/texsmith_template_exam/exam/fillin.py` avec une fonction pure qui retourne `latex` et `width`.
- [x] Remplacer `_replace_fillin_placeholders`, `render_table_fillin_cells`, `render_exam_fillin` pour utiliser la logique commune.
- [x] Ajouter/adapter les tests ciblés pour couvrir les cas `solution` et `width`.

## Phase 3 — Centralisation des modes (solution/compact)
- [ ] Créer `src/texsmith_template_exam/exam/mode.py` pour `_in_solution_mode` et `_in_compact_mode`.
- [ ] Déplacer la logique `_front_matter_flag` et le cache associé dans ce module.
- [ ] Mettre à jour les appels dans les handlers.

## Phase 4 — Découpage par domaine
- [ ] Extraire le rendu des headings vers `src/texsmith_template_exam/exam/headings.py`.
- [ ] Extraire la logique solutions/admonitions/callouts vers `src/texsmith_template_exam/exam/solutions.py`.
- [ ] Extraire la logique `fenced code` vers `src/texsmith_template_exam/exam/fenced_code.py`.
- [ ] Extraire la logique `checkboxes` vers `src/texsmith_template_exam/exam/checkboxes.py`.
- [ ] Garder `exam_renderer.py` comme orchestrateur + `register()`.

## Phase 5 — Assainissement des effets de bord
- [ ] Rendre `exam_markdown_extensions()` pure (ne pas muter `DEFAULT_MARKDOWN_EXTENSIONS`).
- [ ] Encapsuler les caches globaux (`_RENDERER`, `_GIT_VERSION`) ou les déplacer dans un module dédié.
- [ ] Vérifier la compatibilité avec les usages existants.

## Phase 6 — Couche de compatibilité texsmith
- [ ] Créer `src/texsmith_template_exam/exam/texsmith_compat.py` pour isoler les appels aux helpers internes.
- [ ] Remplacer les imports directs dans les handlers.

## Phase 7 — Tests et validation
- [ ] Ajouter des tests unitaires ciblés pour les nouveaux modules.
- [ ] Exécuter l’ensemble de la suite de tests.
- [ ] Documenter les points d’extension si nécessaire.

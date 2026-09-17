# Decision: controlled vocabularies for factors, roles, categories, status and difficulty (issue #19)

Status: **proposal for maintainer decision** (2026-09-17). The mechanical defects listed in issue #19 (stale index count, wrong references, garbled text) are fixed independently; this document settles the vocabularies that the metadata sweep and the validator lint (issue #16, `--lint`) will use.

## 1. Factors

### 1.1 Rules

- Factors are **semantic properties of the history or the fault**, written in lower-case hyphen-case (`multi-file-bfc`), in both suites. Today the normal suite uses hyphens and the graph suite underscores; the sweep converts the graph suite.
- Schema keys, section names and operation names are **not** factors. Operation names are replaced by their semantic equivalent (table below).
- Every scenario has at least one *structure* factor and one *fault* factor. The BIC/BFC count is always stated (`single-bic`/`multi-bic`, `single-bfc`/`multi-bfc`).
- Free-form `<something>-after-bic` tags are replaced by the closest canonical noise factor plus, when useful, a `noise:` note in the README; the title already carries the specific variant.

### 1.2 Canonical structure factors (history shape)

| factor | meaning |
|---|---|
| `single-bic`, `multi-bic` | number of required BICs |
| `single-bfc`, `multi-bfc` | number of BFCs for the bug |
| `linear-history` | single branch (normal suite default) |
| `branch-merge` | BIC and BFC separated by a merge |
| `merge-bic`, `merge-bfc` | the merge commit itself is the BIC / BFC |
| `squash-merge` | single-parent commit carrying a branch result |
| `cherry-pick`, `backport` | replayed commit with a source on another branch |
| `rebase`, `interactive-rebase` | replayed commits with `rebase_of` metadata |
| `conflict-resolution` | merge/rebase/cherry-pick resolved with `resolution` |
| `revert`, `partial-revert`, `revert-of-revert` | reintroduction shapes |
| `release-branch` | maintenance branch involved |
| `origin-vs-direct` | the oracle distinguishes an origin from a direct BIC |
| `copy-propagation`, `clone-divergence` | faulty text copied to another file / copies diverge |
| `deep-line-history` | the faulty line was rewritten by non-BIC commits before the BFC |
| `formatting-noise`, `comment-noise`, `cosmetic-line-noise` | behaviour-preserving edits between BIC and BFC or in the BFC |
| `refactoring-after-bic`, `file-rename`, `file-move`, `method-move`, `method-extract`, `method-inline`, `package-rename` | structural changes between BIC and BFC (replaces `rename_file`, `move_file`, `move_entity`, `copy_entity`, `extract_method`) |
| `tangled-bic`, `tangled-bfc` | the commit mixes the fault/fix with unrelated changes |
| `candidate-selection-distractor` | blame-trivial scenario whose noise commit is a plausible extra candidate |
| `multi-file-bfc`, `multi-hunk-bfc`, `mixed-origin-hunks` | BFC shape |
| `test-line-noise`, `test-only-bic`, `test-file-added` | test code involved |
| `addition-only-fix`, `deletion-only-bic`, `empty-first-parent-fix` | ghost shapes (checked by the validator when declared) |
| `initial-import-bic` | the BIC is a large initial commit |
| `config-bic`, `config-bfc`, `binary-file`, `generated-file`, `file-deletion`, `file-creation-fix`, `file-mode-change`, `non-utf8-file` | non-source / file-level cases (replaces `write_binary_file`, `chmod`, `delete_file`) |
| `generated-history` | commits produced by `commit_generator` |
| `message-evidence`, `issue-evidence`, `work-item`, `misleading-message` | context needed or provided |
| `caller-callee`, `cross-file-cause`, `root-cause-not-in-diff` | non-local evidence |
| `evaluation-variant`, `top-k`, `partial-credit` | oracle policy scenarios (replaces `expected_szz`, `evaluation_variants`) |

### 1.3 Canonical fault factors

`boundary-condition`, `off-by-one`, `wrong-operator`, `boolean-negation`, `wrong-variable`, `wrong-constant`, `null-check-omission`, `missing-break`, `missing-branch`, `guard-removed`, `resource-not-closed`, `exception-swallowed`, `string-comparison`, `integer-overflow`, `api-misuse`, `config-value`, `duplicate-statement`, `composite-fault`.

### 1.4 Synonym table (sweep input)

| today | canonical |
|---|---|
| `multi-bic`, `multiple_bic`, `multiple-bic` | `multi-bic` |
| `single_bfc`, `single-bfc` | `single-bfc` |
| `context`, `context-aware`, `context_dependent` | `message-evidence` or `caller-callee` (per scenario) |
| `multi-file-bfc`, `multi_file`, `multiple_file` | `multi-file-bfc` |
| `formatting`, `formatting_rewrite`, `whitespace-only-after-bic`, `class-body-reformat-after-bic`, … | `formatting-noise` |
| `comment-insertion-after-bic`, `comment-deletion-after-bic`, `comment-only-intermediate` | `comment-noise` |
| `rename_file`, `move_file`, `copy_file`, `delete_file`, `move_entity`, `copy_entity`, `chmod`, `write_binary_file`, `write_generated_text_file`, `commit_generators`, `allow_empty` | `file-rename`, `file-move`, `copy-propagation`, `file-deletion`, `method-move`, `copy-propagation`, `file-mode-change`, `binary-file`, `generated-file`, `generated-history`, (drop) |
| `expected_szz`, `evaluation_variants`, `faults`, `bug_fixing_commits`, `issues`, `work_items`, `clone_relationships`, `bug_instances`, `developer_hints`, `edit`, `drop`, `same_bug`, `root_cause`, `code_interaction` | drop (schema keys) or map: `issues`→`issue-evidence`, `work_items`→`work-item`, `root_cause`→`root-cause-not-in-diff`, `code_interaction`→`caller-callee` |
| `direct_bic`, `origin_bic`, `rebased_bic`, `re_bic`, `dropped_origin_bic` | `origin-vs-direct` (+ `rebase`/`revert` as applicable) |

## 2. Roles

### 2.1 Bug-entry roles (consumed by the evaluator/verifier)

BIC entries: `direct`, `origin`, `contributing`, `reintroducing`. BFC entries: `complete_fix`, `partial_fix`. Everything else (`direct_squash_bic`, `merge_introducing`, `direct_reintroduction`, `origin_bic`, `old_origin_bic`, `related_reintroducing`, `main_fix`, `symptom_fix`, `shared_bfc`, `merge_fix`, `follow_up_fix`, `final_fix`, `attempted_fix`, `backport_fix`, `cherry_picked_release_fix`, `partial_fix_lower_bound`, `complete_fix_upper_bound`, …) is mapped by `normalize_bic_role` (issue #15) and rewritten by the sweep. Narrative detail moves to the entry's `description`.

### 2.2 Commit roles (`commits[].role`)

Keep the normal-suite set as the canonical list for both suites: `initial`, `bug_introducing`, `bug_fixing`, `distractor`, `refactoring`, `formatting`, `test_change`, `merge`, `revert`, `cleanup`, `feature_addition`; add `intermediate` (generic noise), `origin_bug_introducing` (pre-rewrite/copy source), `bug_reintroducing`, `release_branch_point`, `generated` (issue #18). The 29 spellings in use today (`other`, `unrelated`, `candidate`, `prior_fix`, `attempted_fix`, `follow_up_fix`, `work_item_context`, `feature_work`, `source_change`, `semantic_rewrite`, `origin_bug_propagating`, `origin_bug_fixing`, `clone_divergence`, `cherry_pick`, `test_added`, `unfixed_release`, …) are mapped onto this list; the graph validator gains the same `ALLOWED_ROLES` check the normal validator already has (as a `--lint` warning first, an error after the sweep).

## 3. Categories

One code system for both suites, stored as `category_code` and `category` in YAML and index; README files are regenerated from YAML so the legacy "## Source / Category" labels disappear.

| code | name | paper |
|---|---|---|
| S1 | Basic semantic line changes | C1 |
| S2 | Omission and deletion bugs | C2 |
| S3 | Intermediate noise and history noise | C3 |
| S4 | BFC-side noise and tangled commits | C4 |
| S5 | Refactoring, move, and rename after BIC | C5 |
| S6 | Multiple BICs, duplicate faults, and composite faults | C6 |
| S7 | Context, message, and non-local evidence | C7 |
| S8 | Non-source, configuration, test-only, and file-level edge cases | C8 |
| G1 | Refactoring, move, rename, and semantic rewrite | C9 |
| G2 | Clone, copy propagation, and origin-vs-direct BIC | C10 |
| G3 | Multiple BICs, multiple BFCs, and partial fixes | C11 |
| G4 | Branch, merge, cherry-pick, backport, and release branches | C12 |
| G5 | Rebase-specific history rewriting | C13 |
| G6 | Revert-specific reintroduction | C14 |
| G7 | Issue, message, context, and non-local evidence | C15 |
| G8 | Non-source, binary, generated, and scalability edge cases | C16 |
| G9 | Evaluation policy variants | C17 |

Legacy README labels map as follows: "BFC shape scenarios" → S4/G1 by content; "Intermediate-history scenarios" → S3; "Clone propagation scenarios", "Copy, clone, and propagation scenarios" → G2; "Multiple-BIC scenarios", "Multiple BIC and BFC scenarios" → G3; "Branch and merge scenarios", "Branch, merge, cherry-pick, and backport scenarios" → G4; "Revert and reintroduction scenarios" → G6; "Work-item and commit-series scenarios", "Context-dependent scenarios", "Context-aware and LLM-based SZZ scenarios" → G7; "Robustness and implementation-quality scenarios" → G8; "Schema and evaluation-policy scenarios" → G9; "Ambiguous blame …" → S6/G3.

## 4. Status, difficulty, blame class

- `status`: `draft` (may fail lint), `active` (validates with `--strict --lint`, generates, verifies, every Java snapshot compiles, README regenerated, reviewed by a second person), `retired` (kept in `docs/retired-ids.md`, directory removed). Graph scenarios move from `draft` to `active` individually as they pass; the schema version moves from `graph-0.1-draft` to `graph-1.0` when issues #15–#18 have landed and the sweep is complete.
- `blame_class` (new, machine-written by `szzbench stats`/verify): `exact` (plain first-parent blame returns exactly the required set), `extra` (required set plus other candidates), `miss` (a required BIC is not blamed), `addition-only`, `empty-first-parent`. It is measured, never hand-edited.
- `difficulty` stays an author judgement (`easy`/`medium`/`hard`) but must be consistent with `blame_class`: `exact` scenarios are `easy` unless the README names another failure mode; `miss`/`addition-only` scenarios are at least `medium`. The lint warns on inconsistencies.

## 5. Identifiers and index

- Scenario ids are stable and are **not** renumbered. Gaps are documented in `docs/retired-ids.md` (id, former title, reason, replacement).
- `scenario_count` is removed from the index files or recomputed by `szzbench validate-index` (issue #16); it is never hand-edited.
- Index entries are generated from the YAML `meta` block (title, slug, category, factors, difficulty, status, blame_class); the sweep regenerates both index files.

## 6. Sweep plan (after issues #15–#18 land)

1. Apply the factor synonym table and role mapping to all scenarios with a script; commit as one change.
2. Regenerate README files from YAML (single template per suite); remove boilerplate (`Evaluates <title> and checks whether…`, `Draft status`, `c0: c0:` prefixes, stale `difference_from_*` keys, garbled text in SZZG-0046).
3. Run `validate --strict --lint` and `validate-index`; fix residuals; flip `status` to `active` for scenarios that pass.
4. Turn the `--lint` vocabulary warnings into errors.

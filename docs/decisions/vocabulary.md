# Decision: controlled vocabularies for factors, roles, categories, status and difficulty (issue #19)

Status: **decided and applied** (2026-09-19; proposed 2026-09-17; §7 `meta.tier` applied in PR #39). The mechanical defects listed in issue #19 (stale index count, wrong references, garbled text) are fixed independently; this document settles the vocabularies that the metadata sweep and the validator lint (issue #16, `--lint`) will use.

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

**BIC entries** — canonical roles `direct`, `origin`, `contributing`, `reintroducing`. The 23 spellings in use (`direct_squash_bic`, `merge_introducing`, `direct_reintroduction`, `origin_bic`, `old_origin_bic`, `related_reintroducing`, …) are classified by `normalize_bic_role()` (issue #15, PR #27) and rewritten to the canonical spelling by the sweep. `normalize_bic_role()` classifies **BIC roles only**: it returns `other` for every BFC role, including `complete_fix` and `partial_fix`, so it must not be applied to BFC entries.

**BFC entries** — canonical roles `complete_fix` (the commit removes the fault of this bug entry), `partial_fix` (removes part of it; another BFC completes it) and `attempted_fix` (a developer attempt that does **not** remove the fault; kept as context and excluded from the evaluated BFC set). No BFC normalizer exists yet; the sweep applies the table below explicitly, and a `normalize_bfc_role()` should be added next to the BIC one before the migration script runs. Today BFC roles do not influence scoring: the verifier's blame check uses the *last* BFC entry and PR #27's `fix_shape` classifies every listed BFC regardless of role.

| canonical | today (scenarios) |
|---|---|
| `complete_fix` | `complete_fix`; `main_fix` (SZZG-0049, 0050, 0054); `merge_fix` (SZZG-0042, 0046); `final_fix` (SZZG-0085); `complete_fix_upper_bound` (SZZG-0032); `follow_up_fix` (SZZG-0030 c3); `cherry_picked_release_fix` (SZZG-0049 r2) and `backport_fix` (SZZG-0050 r2) — the replay is recorded by `cherry_pick_of`/`backport_of`, not by the role; `shared_bfc` (SZZG-0034 c3: one commit that completely fixes each of two bug entries) |
| `partial_fix` | `partial_fix`; `partial_fix_lower_bound` (SZZG-0032 c2) |
| classified per bug entry | `symptom_fix` (SZZG-0035): the scenario declares **two** bug entries — B001 (`acceptImport`, single BFC c2) and B002 (`acceptSearch`, single BFC c3) — and each BFC completely restores its method's inclusive check, so both map to `complete_fix` with the symptom detail kept in `description`. Narrative roles like this are classified by the repair's scope *within its own bug entry*, never by an unconditional string mapping; a `symptom_fix` would be `partial_fix` only where the same bug entry lists another BFC that completes the repair |
| `attempted_fix` | `attempted_fix` (SZZG-0030 c2; under D6 of the origin/direct contract it is also the direct BIC of the new `\|\|` fault) |

Narrative detail ("main-line fix", "release fix", "upper bound") moves to the entry's `description`.

### 2.2 Commit roles (`commits[].role`)

Keep the normal-suite set as the canonical list for both suites: `initial`, `bug_introducing`, `bug_fixing`, `distractor`, `refactoring`, `formatting`, `test_change`, `merge`, `revert`, `cleanup`, `feature_addition`; add `intermediate` (generic noise), `origin_bug_introducing` (pre-rewrite/copy source), `bug_reintroducing`, `release_branch_point`, `generated` (issue #18). The 29 spellings in use today (`other`, `unrelated`, `candidate`, `prior_fix`, `attempted_fix`, `follow_up_fix`, `work_item_context`, `feature_work`, `source_change`, `semantic_rewrite`, `origin_bug_propagating`, `origin_bug_fixing`, `clone_divergence`, `cherry_pick`, `test_added`, `unfixed_release`, …) are mapped onto this list; the graph validator gains the same `ALLOWED_ROLES` check the normal validator already has (as a `--lint` warning first, an error after the sweep).

## 3. Categories

One code system for both suites, stored as `category_code` and `category` in YAML and index. Every README states the code and name in its generated header (`szzbench readme`, [scenario-readme.md](../scenario-readme.md)); the legacy "## Source / Category" labels were removed with the header's introduction on 2026-09-22, and `W455` / `GW455` reports one that comes back. The paper's C1–C17 numbering stays in this table only.

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

- `status`: `draft` (may fail lint), `active` (validates with `--strict --lint`, generates, verifies, every Java snapshot compiles (every Python snapshot byte-compiles; see the Python clause below), README regenerated, reviewed by a second person), `retired` (kept in `docs/retired-ids.md`, directory removed). Graph scenarios move from `draft` to `active` individually as they pass; the schema version moves from `graph-0.1-draft` to `graph-1.0` when issues #15–#18 have landed and the sweep is complete. **Both happened on 2026-09-19**: #15–#18 are closed and the metadata sweep landed in #46 and #47. Clause by clause, the `active` bar stands as follows. *Validates under `--strict --lint`*: 114/114. *Generates and verifies*: 114/114. *Every Java snapshot compiles*: 1513/1513 Java-bearing commit snapshots across the 114 graph repositories (of 1514 snapshots in total; one carries no Java) — the last three that did not (SZZG-0001, SZZG-0003 and SZZG-0017, each a public class whose name did not match its file) were repaired first, which also closes the remainder of issue #10. *Reviewed by a second person*: every scenario reached `active` through PR review. *README regenerated*: **partially**, and deliberately so. The boilerplate this flip would otherwise have falsified is gone (the `Draft status` section, removed from all 52 READMEs that carried it) and every machine-shaped `## Expected history` block is re-derived from its YAML, so no README contradicts its artifact. The single-template regeneration of §6 step 2 was not run — see that step.
- **What "every Java snapshot compiles" means** (decided 2026-09-19, issue #50). A snapshot must compile with `javac` over its own source tree, **unless** the repository declares the missing dependency in a build file and `repository.build_system` names that build system; such a snapshot is out of scope for the bar. A benchmark that forbids external dependencies cannot represent a dependency-update BIC, and that is a real SZZ failure mode — SZZ-0171 is the suite's only scenario with a build file, and its BIC touches nothing but `pom.xml`. A symbol that is declared *nowhere* is a defect rather than an exemption: SZZ-0005 applied an `@Required` annotation it never defined and SZZ-0168 imported JUnit with no build file, and both were repaired. Measured 2026-09-19 across both suites: 1929 commit snapshots, of which 1928 carry Java; all compile except SZZ-0171's three, which the exemption covers.
- **Python scenarios and the compile bar** (decided 2026-09-21, issue #24). `repository.language` was `java` in every scenario until SZZ-0200–SZZ-0206 introduced Python twins and variants of S1–S3 (a wrong constant mirrored from SZZ-0021, `//` mistaken for a typo, a mutable default argument, a missing key check mirrored from SZZ-0047, a type-annotation rewrite and an f-string conversion of the faulty line, and a BOM-only re-save). The bar is the same sentence with the language's notion of compiling: *every Python snapshot byte-compiles* (`py_compile`, CPython 3). Unlike the Java bar it is checked on every test run — `tests/test_python_scenarios.py` generates the seven repositories and byte-compiles every `.py` file of every commit (24/24 snapshots on 2026-09-21), and runs each module at each commit so the fault is observed at the BIC, through the noise commit and gone at the BFC — because the interpreter running the tests is the only toolchain it needs. No Python scenario declares a dependency, so the build-file exemption does not arise. Other languages are out of scope until a scenario needs them; a C or JavaScript variant would have to state its own bar (`cc -fsyntax-only`, `node --check`) and the toolchain the repository then requires.
- `blame_class` is **specified but not implemented** (checked 2026-09-19). The intended values are `exact` (plain first-parent blame returns exactly the required set), `extra` (required set plus other candidates), `miss` (a required BIC is not blamed), `addition-only` and `empty-first-parent`, measured and never hand-edited. Today nothing in `src/` writes or reads the field, there is no `szzbench stats` command (the fault-statement reuse statistic of issue #13, once assigned to it, lives in `szzbench coverage` since 2026-09-21), and no scenario declares it. Implementing it is the prerequisite for grading `difficulty` below, and the two should land together.
- `difficulty` is an author judgement. The classic suite uses `easy`/`medium`/`hard` (29/45/37 as of 2026-09-19); the graph suite declares `advanced` for all 114 scenarios, which means *not graded on the classic scale*, not *harder than `hard`*. **Decided 2026-09-19: the graph suite keeps `advanced` and is not re-graded by hand.** The grading rule this document states is defined against `blame_class`, so grading now would mean inventing a different rule and then having to re-grade again once the measurement exists. When `blame_class` lands, the graph suite is graded from it — `exact` is `easy` unless the README names another failure mode, `miss`/`addition-only` is at least `medium` — and the consistency lint that enforces the rule becomes implementable. That lint does not exist yet; neither `difficulty` nor the copy of it in `scenarios/index.yml` is validated against anything today.

## 5. Identifiers and index

- Scenario ids are stable and are **not** renumbered. Gaps are documented in `docs/retired-ids.md` (id, former title, reason, replacement).
- `scenario_count` is removed from the index files or recomputed by `szzbench validate-index` (issue #16); it is never hand-edited.
- Index entries are generated from the YAML `meta` block (title, slug, category, factors, difficulty, status, and `blame_class` once §4's field exists); the sweep regenerates both index files. `title`, `factors` and `status` are checked against the scenario by IE041/IE043/IE045; `difficulty` is copied into `scenarios/index.yml` but checked by nothing.

## 6. Sweep plan (after issues #15–#18 land)

1. Apply the factor synonym table and role mapping to all scenarios with a script; commit as one change.
2. Regenerate README files from YAML (single template per suite); remove boilerplate (`Evaluates <title> and checks whether…`, `Draft status`, `c0: c0:` prefixes, stale `difference_from_*` keys, garbled text in SZZG-0046). **Re-scoped and done on 2026-09-22 (issue #19).** A single template would have overwritten the hand-written prose that 98 of the graph READMEs had gained in #41–#47, so the regeneration was defined as *augmenting*: every README opens with a **generated header** — title, category code and name, tier, status, difficulty, language, factors, the oracle as the evaluator resolves it and, in the graph suite, the graph-only features the scenario uses — rendered by `szzbench readme` and checked by `W455` / `GW455`; everything after it is the author's ([scenario-readme.md](../scenario-readme.md)). The hand-written `## Factors` and `## Source` copies (8 of the former disagreed with the YAML, 35 of the latter used the legacy category names) were removed by the same command. Gone earlier, on 2026-09-19: the `Draft status` sections (52), the `c0: c0:` prefixes, SZZG-0046's garbled text; the `## Expected history` blocks are re-derived from the YAML (`GW454`). The template-era boilerplate sections and the `Evaluate <title> and whether…` purposes of the 44 oldest graph READMEs, and the `current_schema_limitation` boilerplate in their YAML, are handled by the follow-up PR of issue #19.
3. Run `validate --strict --lint` and `validate-index`; fix residuals; flip `status` to `active` for scenarios that pass.
4. Turn the `--lint` vocabulary warnings into errors. **Done 2026-09-22**: `W400`–`W402` and `GW400`–`GW404` are `E400`–`E402` / `GE400`–`GE404`; both suites were at zero findings when the severity changed.

## 7. `meta.tier`: what a scenario is for (issue #14)

Added 2026-09-18. Every scenario declares one of two values.

| tier | meaning |
|---|---|
| `control` | The scenario checks that a method handles a specific input condition. A cheap rule may well solve it; that is expected of a control, and failing it means the method is broken on that condition. |
| `discriminating` | The scenario is designed so that none of the declared cheap baselines solves it, so it separates methods rather than only checking them. |

The tier is a **declaration**, not a measurement: it says what the scenario is
for. `szzbench baselines` then checks the declaration against the suite and
reports any scenario declared `discriminating` that a cheap rule solves, and
any `control` that no cheap rule solves (a promotion candidate).
`validate --lint` requires the field and the vocabulary (`W460` / `GW460`).

The initial assignment followed the measurement at `6ed60a0`: **203 control and
7 discriminating** — SZZ-0132, SZZ-0136, SZZG-0028, SZZG-0038, SZZG-0040,
SZZG-0069 and SZZG-0076, all of which have a multi-commit oracle. Fifteen
scenarios designed against that axis have been added since, so the suite now
declares **203 control and 22 discriminating**; the list and the reasons are in
[baselines.md](../baselines.md#the-two-tiers).

A declaration is a claim the measurement can refuse, and has. SZZG-0118 was
declared `discriminating` and `szzbench baselines` reported it solved: the
generator's author rotation had given its two bug-introducing commits the same
author and no other commit that author, so an author rule returned exactly the
oracle by coincidence. The scenario was changed, not the declaration.

The tier is **not** mirrored in `index.yml`. The index is not checked against
it, and a second copy of a field that changes with the scenario is how the
index drifted before (issue #19). The scenario file is the single source of
truth; `szzbench coverage --json` joins the tier with the difficulty
dimensions for anyone who wants to select on it.


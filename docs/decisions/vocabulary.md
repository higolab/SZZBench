# Decision: controlled vocabularies for factors, roles, categories, status and difficulty (issue #19)

Status: **decided and applied** (2026-09-19; proposed 2026-09-17; §7 `meta.tier` applied in PR #39; on 2026-10-10 the factor vocabulary of §1 was opened (issues #196, #197), every old spelling of §1.4 was replaced (issue #197 and a follow-up) and `attempted_fix` left the BFC roles of §2.1 (issue #187); the same day the commit roles of §2.2 were mapped and checked in both suites (issue #195), `meta.status` was checked (issue #157) and every `discriminating` scenario came to declare `meta.defeats` (issue #207)). The mechanical defects listed in issue #19 (stale index count, wrong references, garbled text) are fixed independently; this document settles the vocabularies that the metadata sweep and the validator lint (issue #16, `--lint`) will use.

## 1. Factors

### 1.1 Rules

The factor vocabulary is **open** (decided 2026-10-10, issue #197). §1.2 and §1.3 list the **recommended** words: an author uses a listed word where one fits, and may add any other tag that names a property the lists do not have. No lint reports a factor outside the lists: `--lint` checks a factor's style and refuses schema keys and operation names (below), and does not ask whether the word is listed.

- Factors are **semantic properties of the history or the fault**, written in lower-case hyphen-case (`multi-file-bfc`), in both suites. The graph suite used underscores until its lists were normalised to hyphen-case on 2026-09-19 (PR #46); `E402` / `GE402` report a scenario that mixes the two styles.
- Schema keys, section names and operation names are **not** factors (`E400` / `GE400`). Operation names are replaced by their semantic equivalent (§1.4).
- A scenario names at least one *structure* factor and one *fault* factor where it can, and `meta.factors` is never empty (`E401` / `GE401`). Nothing checks the first part: on 2026-10-10, 261 of the 279 shipped scenarios named a listed structure factor and 76 a listed fault factor. The number of BICs and BFCs is **not** required as a factor (issue #196): it is a property of the oracle, which the README header's `oracle` row shows and `szzbench coverage` measures (`oracle_size`), the way §4 measures `blame_class` instead of declaring it. `single-bic`/`multi-bic` and `single-bfc`/`multi-bfc` stay in §1.2 for the scenarios that declare them.
- A specific variant may be a tag of its own (`import-reorder-after-bic`, `lambda-rewrite-after-bic`); the title usually names it as well. The listed word for its class (`formatting-noise`, `comment-noise`, `cosmetic-line-noise`, `refactoring-after-bic`) is the recommended companion.
- Some checks read a factor as a **declaration**, so a free tag can mean something to the validator. A factor *containing* one of a few substrings silences W301, W320, W330, W420, W430 and W431, and turns the verifier's W701 / GW701 into I701 / GI701 (`after-bic`, `format`, `noise`, `duplicate`, `root-cause` and the rest are listed with each code in [validation.md](../validation.md)). Replacing a tag by a listed word can therefore change what is declared: `comment-insertion-after-bic` contains `after-bic`, which silences W430, and `comment-noise` contains `noise`, which silences W420 and W431 instead. A few exact words declare a shape a check then holds the scenario to (`addition-only-fix` for W420, `deletion-only-bic` for W421) or allow what a check otherwise refuses (`gitattributes-bic`, E051 / GE063).

### 1.2 Recommended structure factors (history shape)

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

### 1.3 Recommended fault factors

`boundary-condition`, `off-by-one`, `wrong-operator`, `boolean-negation`, `wrong-variable`, `wrong-constant`, `null-check-omission`, `missing-break`, `missing-branch`, `guard-removed`, `resource-not-closed`, `exception-swallowed`, `string-comparison`, `integer-overflow`, `api-misuse`, `config-value`, `duplicate-statement`, `composite-fault`.

### 1.4 Old spellings (synonym table)

The table was the input of the sweep (§6 step 1). Its first column is spelled as the scenarios spelled it then, before the graph suite's lists became hyphen-case. A spelling it names is replaced by the word in the second column, and a new scenario does not use it. Since 2026-10-10 no shipped scenario uses one; what was applied, and where a scenario called for another word than the table's, is listed below the table.

| old spelling | replacement |
|---|---|
| `multi-bic`, `multiple_bic`, `multiple-bic` | `multi-bic` |
| `single_bfc`, `single-bfc` | `single-bfc` |
| `context`, `context-aware`, `context_dependent` | `message-evidence` or `caller-callee` (per scenario) |
| `multi-file-bfc`, `multi_file`, `multiple_file` | `multi-file-bfc` |
| `formatting`, `formatting_rewrite`, `whitespace-only-after-bic`, `class-body-reformat-after-bic` | `formatting-noise` |
| `comment-insertion-after-bic`, `comment-deletion-after-bic`, `comment-only-intermediate` | `comment-noise` |
| `rename_file`, `move_file`, `copy_file`, `delete_file`, `move_entity`, `copy_entity`, `chmod`, `write_binary_file`, `write_generated_text_file`, `commit_generators`, `allow_empty` | `file-rename`, `file-move`, `copy-propagation`, `file-deletion`, `method-move`, `copy-propagation`, `file-mode-change`, `binary-file`, `generated-file`, `generated-history`, (drop) |
| `expected_szz`, `evaluation_variants`, `faults`, `bug_fixing_commits`, `issues`, `work_items`, `clone_relationships`, `bug_instances`, `developer_hints`, `edit`, `drop`, `same_bug`, `root_cause`, `code_interaction` | drop (schema keys) or map: `issues`→`issue-evidence`, `work_items`→`work-item`, `root_cause`→`root-cause-not-in-diff`, `code_interaction`→`caller-callee` |
| `direct_bic`, `origin_bic`, `rebased_bic`, `re_bic`, `dropped_origin_bic` | `origin-vs-direct` (+ `rebase`/`revert` as applicable) |

What has been applied:

- **2026-09-19 (PR #46).** Every spelling that `E400` / `GE400` now reject: the schema keys and operation names of `RESERVED_FACTOR_WORDS`.
- **2026-10-10 (issue #197).** The rows for `context`, formatting and comments, to the ten spellings still in use: `context` (5 scenarios), `context-aware` (3), `context-dependent` (5), and `formatting`, `formatting-rewrite`, `whitespace-only-after-bic`, `class-body-reformat-after-bic`, `comment-insertion-after-bic`, `comment-deletion-after-bic` and `comment-only-intermediate` (1 each). Per scenario, `context` became `message-evidence` where a message is the evidence (SZZ-0166, SZZ-0168, SZZG-0098) and `caller-callee` where the code that calls or reads the faulty code is (SZZ-0172, SZZG-0038, SZZG-0040, SZZG-0104, SZZG-0105). Where the scenario already declared a word of the same row or group, the old spelling was dropped instead: `message-evidence` (SZZ-0159), `caller-callee` (SZZG-0101, SZZG-0103), `misleading-message` (SZZ-0158, whose message is evidence to reject, the contrast with its twin SZZ-0159) and `issue-evidence` (SZZG-0102, whose commit subjects carry only issue identifiers).
- **2026-10-10 (follow-up to issue #197).** The hyphen-case forms of the rest, in 39 scenarios: the last row's `origin-bic`, `direct-bic`, `re-bic`, `rebased-bic` and `dropped-origin-bic` (33 graph scenarios), `multi-file` / `multiple-file` (SZZG-0083, SZZG-0037), `root-cause` (SZZ-0169, SZZG-0035), `code-interaction` (SZZ-0172) and `same-bug` (SZZ-0154, SZZG-0032). The last row's spellings became `origin-vs-direct` in the 32 scenarios whose oracle lists related origins beside the required BIC; each of them that rebases or reverts already declared `rebase` or a word of §1.2's revert row, so neither was added. Per scenario: SZZG-0065's `direct-bic` was dropped, since its oracle has no origin (the rebase's conflict resolution writes the fault, as `conflict-resolution-bic` and `fault-in-neither-parent` say); SZZG-0072's `dropped-origin-bic` became `origin-vs-direct` and `dropped-commit`, the interactive rebase's action, as `squash` and `reorder` name theirs in SZZG-0070 and SZZG-0073; SZZG-0083's `multi-file` became `multi-file-bic`, not `multi-file-bfc`, because its bug-introducing commit is the one that spans three files, while SZZG-0037's `multiple-file` did become `multi-file-bfc`; `root-cause` became `root-cause-not-in-diff` (in both scenarios the fix leaves the faulty line alone); `code-interaction` and `same-bug` were dropped, since SZZ-0172 declares `caller-callee` and the two scenarios with `same-bug` already say that their commits belong to one bug (`multi-bic` and `composite-bug`; `multi-bfc`). Tags that merely contain one of these spellings (`origin-and-direct-bic`, `multiple-origin-bic`, `origin-bic-policy`, `direct-bic-in-copy`, `root-cause-not-touched`) are free tags (§1.1) and stay.

## 2. Roles

### 2.1 Bug-entry roles (consumed by the evaluator/verifier)

**BIC entries** — canonical roles `direct`, `origin`, `contributing`, `reintroducing`. The 23 spellings in use (`direct_squash_bic`, `merge_introducing`, `direct_reintroduction`, `origin_bic`, `old_origin_bic`, `related_reintroducing`, …) are classified by `normalize_bic_role()` (issue #15, PR #27) and rewritten to the canonical spelling by the sweep. `normalize_bic_role()` classifies **BIC roles only**: it returns `other` for every BFC role, including `complete_fix` and `partial_fix`, so it must not be applied to BFC entries.

**BFC entries** — canonical roles `complete_fix` (the commit removes the fault of this bug entry) and `partial_fix` (removes part of it; another BFC completes it). Every BFC entry is a fix the evaluator scores. A developer's attempt that does **not** remove the fault is not a BFC entry: it is an ordinary commit with a role of §2.2 (decided 2026-10-10, issue #187; §2.2 has no role for an attempt as such: SZZG-0030 c2, the one commit that was `attempted_fix`, is the direct BIC of B002 and became `bug_introducing`, issue #195). Until then this paragraph listed a third BFC role, `attempted_fix`, "kept as context and excluded from the evaluated BFC set"; no code excluded such an entry, `validate-graph --lint` rejected the spelling (`GE404`), and no shipped BFC entry declared it. BFC roles are not normalized: the sweep applied the table below explicitly, no BFC counterpart of `normalize_bic_role()` was written, and every shipped BFC entry now declares `complete_fix` (153) or `partial_fix` (6). `validate-graph --lint` accepts those two spellings only (`GE404`). Today BFC roles do not influence scoring: the verifier's blame check uses the *last* BFC entry and PR #27's `fix_shape` classifies every listed BFC regardless of role.

| canonical | today (scenarios) |
|---|---|
| `complete_fix` | `complete_fix`; `main_fix` (SZZG-0049, 0050, 0054); `merge_fix` (SZZG-0042, 0046); `final_fix` (SZZG-0085); `complete_fix_upper_bound` (SZZG-0032); `follow_up_fix` (SZZG-0030 c3); `cherry_picked_release_fix` (SZZG-0049 r2) and `backport_fix` (SZZG-0050 r2) — the replay is recorded by `cherry_pick_of`/`backport_of`, not by the role; `shared_bfc` (SZZG-0034 c3: one commit that completely fixes each of two bug entries) |
| `partial_fix` | `partial_fix`; `partial_fix_lower_bound` (SZZG-0032 c2) |
| classified per bug entry | `symptom_fix` (SZZG-0035): the scenario declares **two** bug entries — B001 (`acceptImport`, single BFC c2) and B002 (`acceptSearch`, single BFC c3) — and each BFC completely restores its method's inclusive check, so both map to `complete_fix` with the symptom detail kept in `description`. Narrative roles like this are classified by the repair's scope *within its own bug entry*, never by an unconditional string mapping; a `symptom_fix` would be `partial_fix` only where the same bug entry lists another BFC that completes the repair |
| not a BFC role | `attempted_fix` (SZZG-0030 c2). The commit does remove B001's exclusive bounds, so B001 lists it as `complete_fix` (issue #3); under D6 of the origin/direct contract it is also the direct BIC of B002, the new `\|\|` fault. That it was an attempt was the commit's role, `commits[].role: attempted_fix`; §2.2's mapping made it `bug_introducing`, the role of a commit in the scenario's `required` set (issue #195) |

Narrative detail ("main-line fix", "release fix", "upper bound") moves to the entry's `description`.

### 2.2 Commit roles (`commits[].role`)

Keep the normal-suite set as the canonical list for both suites: `initial`, `bug_introducing`, `bug_fixing`, `distractor`, `refactoring`, `formatting`, `test_change`, `merge`, `revert`, `cleanup`, `feature_addition`; add `intermediate` (generic noise), `origin_bug_introducing` (pre-rewrite/copy source), `bug_reintroducing`, `release_branch_point`, `generated` (issue #18). The list is `ALLOWED_ROLES` in `validator.py`, defined once for both suites: `validate` reports any other role (`E030`, a default check, as it always has; the five additions are accepted there too), and `validate-graph --lint` reports it as well (`GE405`, an error like the other vocabulary lints, issue #195). A role describes the commit for a reader: it is copied into `commit-map.json` and read by no scorer, which reads the roles of the bug entries (§2.1) instead.

The graph validator gained the check on 2026-10-10 (issue #195), when 28 commits in 22 graph scenarios still carried 16 spellings outside the list; the classic suite used only the first eleven. They were mapped as follows, and the replay of a cherry-pick, a backport or a rebase stays recorded by `cherry_pick_of`, `backport_of` and `rebase_of`, not by the role:

| old spelling | canonical | commits |
|---|---|---|
| `other` | `intermediate` | SZZG-0026 c1, SZZG-0041 c2, SZZG-0059 c1 and c2, SZZG-0060 c2, SZZG-0062 c2 |
| `unrelated`, `work_item_context`, `feature_work` | `intermediate` | SZZG-0100 c2 and c3; SZZG-0097 c1 and c3; SZZG-0093 c1 and c3 |
| `source_change`, `clone_divergence`, `unfixed_release` | `intermediate` | SZZG-0051 c1; SZZG-0017 c2; SZZG-0054 c4 |
| `cherry_pick`, `attempted_fix` | `bug_introducing` | SZZG-0048 r1 (B001's only direct BIC; `cherry_pick_of: c1` records the replay); SZZG-0030 c2 (B002's direct BIC, and B001's `complete_fix`) |
| `candidate` | `distractor` | SZZG-0096 c1 and c3 |
| `test_added` | `test_change` | SZZG-0036 c2 (issue #198) |
| `refactor`, `semantic_rewrite` | `refactoring` | SZZG-0119 c2; SZZG-0008 c2 |
| `prior_fix`, `follow_up_fix`, `origin_bug_fixing` | `bug_fixing` | SZZG-0088 c2, SZZG-0089 c2, SZZG-0091 c3; SZZG-0030 c3; SZZG-0015 c3, SZZG-0058 f2 |
| `origin_bug_propagating` | `origin_bug_introducing` | SZZG-0023 f2 |

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

- `status`: `draft` (may fail lint), `active` (validates with `--strict --lint`, generates, verifies, every Java snapshot compiles (every Python snapshot byte-compiles; see the Python clause below), README regenerated, reviewed by a second person), `retired` (kept in `docs/retired-ids.md`, directory removed). Graph scenarios move from `draft` to `active` individually as they pass; the schema version moves from `graph-0.1-draft` to `graph-1.0` when issues #15–#18 have landed and the sweep is complete. **Both happened on 2026-09-19**: #15–#18 are closed and the metadata sweep landed in #46 and #47. Clause by clause, the `active` bar stands as follows. *Validates under `--strict --lint`*: 114/114. *Generates and verifies*: 114/114. *Every Java snapshot compiles*: 1513/1513 Java-bearing commit snapshots across the 114 graph repositories (of 1514 snapshots in total; one carries no Java) — the last three that did not (SZZG-0001, SZZG-0003 and SZZG-0017, each a public class whose name did not match its file) were repaired first, which also closes the remainder of issue #10. *Reviewed by a second person*: every scenario reached `active` through PR review. *README regenerated*: **partially**, and deliberately so. The boilerplate this flip would otherwise have falsified is gone (the `Draft status` section, removed from all 52 READMEs that carried it) and every machine-shaped `## Expected history` block is re-derived from its YAML, so no README contradicts its artifact. The single-template regeneration of §6 step 2 was not run — see that step. `validate` and `validate-graph` report a `meta.status` outside these three words (`W002` / `GW018`, a warning that `--strict` fails on; issue #157); until then no check read the field.
- **What "every Java snapshot compiles" means** (decided 2026-09-19, issue #50). A snapshot must compile with `javac` over its own source tree, **unless** the repository declares the missing dependency in a build file and `repository.build_system` names that build system; such a snapshot is out of scope for the bar. A benchmark that forbids external dependencies cannot represent a dependency-update BIC, and that is a real SZZ failure mode — SZZ-0171 is the suite's only scenario with a build file, and its BIC touches nothing but `pom.xml`. A symbol that is declared *nowhere* is a defect rather than an exemption: SZZ-0005 applied an `@Required` annotation it never defined and SZZ-0168 imported JUnit with no build file, and both were repaired. Measured 2026-09-19 across both suites: 1929 commit snapshots, of which 1928 carry Java; all compile except SZZ-0171's three, which the exemption covers.
- **Python scenarios and the compile bar** (decided 2026-09-21, issue #24). `repository.language` was `java` in every scenario until SZZ-0200–SZZ-0206 introduced Python twins and variants of S1–S3 (a wrong constant mirrored from SZZ-0021, `//` mistaken for a typo, a mutable default argument, a missing key check mirrored from SZZ-0047, a type-annotation rewrite and an f-string conversion of the faulty line, and a BOM-only re-save). The bar is the same sentence with the language's notion of compiling: *every Python snapshot byte-compiles* (`py_compile`, CPython 3). Unlike the Java bar it is checked on every test run — `tests/test_python_scenarios.py` generates the seven repositories and byte-compiles every `.py` file of every commit (24/24 snapshots on 2026-09-21), and runs each module at each commit so the fault is observed at the BIC, through the noise commit and gone at the BFC — because the interpreter running the tests is the only toolchain it needs. No Python scenario declares a dependency, so the build-file exemption does not arise. Other languages are out of scope until a scenario needs them; a C or JavaScript variant would have to state its own bar (`cc -fsyntax-only`, `node --check`) and the toolchain the repository then requires.
- `blame_class` is **measured by `szzbench coverage` since 2026-09-22** (issue #35). The values are `exact` (plain first-parent blame on the lines every bug-fixing commit deletes returns exactly the required set), `extra` (the required set and other commits), `miss` (a required commit is not blamed), `addition-only` (no fix deletes a line) and `empty-first-parent` (every fix is a merge whose first-parent diff is empty); an empty oracle with any blamed commit is `extra`. It is measured from the generated repository, reported per scenario in `coverage.json` (`shapes[].blame_class`) and as a distribution, and is **never written into a scenario file** — a hand-edited copy would drift like the README factor lists did (issue #19). It is not part of the redundancy signature. The same report tabulates the declared `difficulty` against it (`difficulty_by_blame_class`), which is the input the grading rule below is checked with. The measurement agrees with the `blame-deleted-lines` baseline scenario by scenario, except where a policy other than `exact_set` accepts a partial blame (SZZG-0138, `partial_credit`).
- `difficulty` is a graded author judgement with a **measured floor** (decided 2026-09-22, issue #35). The vocabulary is `easy` / `medium` / `hard` (`W461` / `GW461`); `advanced`, the graph suite's placeholder for *not graded on the classic scale*, is retired. The floor is set by the scenario's `blame_class`: `exact` → `easy`, `extra` → `medium`, `addition-only` → `medium`, `miss` → `hard`, `empty-first-parent` → `hard`. A scenario **may declare more** than its floor when its README names a failure mode other than blame (the classic suite has 40 such overrides, e.g. the S6/S7/S8 scenarios that are `exact` but `hard` because the answer needs context); it **may not declare less**. `szzbench coverage` reports every declaration below the floor as a contradiction to fix, lists the overrides, and lists ungraded declarations; the check needs the generated repository, so it lives there rather than in `validate`. Applied 2026-09-22: the graph suite was graded mechanically from its floors (93 `easy`, 10 `medium`, 33 `hard`, from `advanced` throughout), and the eight classic scenarios below their floor were raised — SZZ-0203 (`addition-only`, `easy` → `medium`) and SZZ-0081, 0082, 0083, 0136, 0204, 0205, 0206 (`miss`, `medium` → `hard`; only SZZ-0083 is recovered by `git blame -w`, and the floor is measured with plain blame) — each with a `## Difficulty` note in its README recording the author's grade. Raising a graph scenario above its floor where its README names another failure mode is the G4–G8 audit's job. This replaces the 2026-09-19 decision to keep `advanced` until the measurement existed.

## 5. Identifiers and index

- Scenario ids are stable and are **not** renumbered. Gaps are documented in `docs/retired-ids.md` (id, former title, reason, replacement).
- **Both index files have one shape** (decided 2026-10-10, issue #200): a top-level `scenarios` list and nothing else, and entries with `id`, `title`, `slug`, `category_code`, `category`, `factors`, `difficulty`, `status`, `path` and `readme`, in that order. The graph index used to describe itself as a draft (`schema_version: graph-index-0.1-draft`, a `description` of "draft advanced graph scenarios") and to carry a `scenario_count` and `notes`, and its entries had no `slug` and no `difficulty`; the classic entries had no `readme`. `scenario_count` repeated the length of the list, and nothing but `IE010` (issue #16) read it, while `new-graph-scenario` had to raise it (issue #111); it was dropped with `IE010` and `IE011`, and a key other than `scenarios` is `IW004`. `new-scenario`, `new-graph-scenario` and the Scenario Editor write entries of this shape.
- Index entries are generated from the YAML `meta` block (title, slug, category code and name, factors, difficulty, status); `path` and `readme` name the scenario file and the README. Both index files were regenerated so on 2026-10-10 (issue #200). `title`, `factors` and `status` are checked against the scenario by IE041/IE043/IE045, `slug`, `category`, `category_code` and `difficulty` by IE046, which also reports an entry that lacks one of the keys, and `readme` by IE024; the value of `difficulty` itself is checked against its measured floor by `szzbench coverage` (§4). `blame_class` is not in the index: it is measured, never written into a scenario file (§4).

## 6. Sweep plan (after issues #15–#18 land)

1. Apply the factor synonym table and role mapping to all scenarios with a script; commit as one change. **Done for the factors and the bug-entry roles, in two parts.** On 2026-09-19 (PR #46) the bug-entry roles were migrated (§2.1), the schema keys and operation names among the factors replaced and the graph suite's factor lists normalised to hyphen-case. On 2026-10-10 (issue #197) the vocabulary was declared open (§1.1) rather than closed by a lint, and §1.4 was applied to the ten old spellings still in use and, the same day, to the hyphen-case forms of the rest (39 scenarios), so no shipped scenario uses a spelling of §1.4. The commit roles of §2.2 were mapped on 2026-10-10 (issue #195), and `GE405` checks them.
2. Regenerate README files from YAML (single template per suite); remove boilerplate (`Evaluates <title> and checks whether…`, `Draft status`, `c0: c0:` prefixes, stale `difference_from_*` keys, garbled text in SZZG-0046). **Re-scoped and done on 2026-09-22 (issue #19).** A single template would have overwritten the hand-written prose that 98 of the graph READMEs had gained in #41–#47, so the regeneration was defined as *augmenting*: every README opens with a **generated header** — title, category code and name, tier, status, difficulty, language, factors, the oracle as the evaluator resolves it and, in the graph suite, the graph-only features the scenario uses — rendered by `szzbench readme` and checked by `W455` / `GW455`; everything after it is the author's ([scenario-readme.md](../scenario-readme.md)). The hand-written `## Factors` and `## Source` copies (8 of the former disagreed with the YAML, 35 of the latter used the legacy category names) were removed by the same command. Gone earlier, on 2026-09-19: the `Draft status` sections (52), the `c0: c0:` prefixes, SZZG-0046's garbled text; the `## Expected history` blocks are re-derived from the YAML (`GW454`). The template-era boilerplate went the same day in the second PR of issue #19: in the 44 oldest graph READMEs the `Evaluate <title> and whether…` purposes were replaced by the scenario's own `scenario_design.purpose`, and the generic `Why this needs scenario.graph.yml` sentence, the `Required graph-schema features` list, the three generic `Evaluation points`, the bare `Expected BICs` code blocks and the `Files` tree were removed (hand-written bodies under the same headings stayed); in the YAML, the generic `current_schema_limitation` sentence (39 scenarios; the 11 hand-written ones stay), every `required_extensions_from_source` (49, all `This scenario uses factors: …; operations: …`, with pre-sweep factor names) and the generic three-bullet `evaluation_points` (32) were removed. The classic `Evaluates <title> and checks whether…` descriptions (SZZ-0155, SZZ-0156, SZZ-0171) and SZZ-0103's garbled description were rewritten. `tests/test_shipped_metadata.py` keeps the sentences from coming back.
3. Run `validate --strict --lint` and `validate-index`; fix residuals; flip `status` to `active` for scenarios that pass.
4. Turn the `--lint` vocabulary warnings into errors. **Done 2026-09-22**: `W400`–`W402` and `GW400`–`GW404` are `E400`–`E402` / `GE400`–`GE404`; both suites were at zero findings when the severity changed.

## 7. `meta.tier`: what a scenario is for (issue #14)

Added 2026-09-18. Every scenario declares one of two values.

| tier | meaning |
|---|---|
| `control` | The scenario checks that a method handles a specific input condition. A naive rule may well solve it; that is expected of a control, and failing it means the method is broken on that condition. |
| `discriminating` | The scenario is designed so that none of the declared naive baselines solves it, so it separates methods rather than only checking them. |

The tier is a **declaration**, not a measurement: it says what the scenario is
for. `szzbench baselines` then checks the declaration against the suite and
reports any scenario declared `discriminating` that a naive rule solves, and
any `control` that no naive rule solves (a promotion candidate).
`validate --lint` requires the field and the vocabulary (`W460` / `GW460`).

The initial assignment followed the measurement at `6ed60a0`: **203 control and
7 discriminating** — SZZ-0132, SZZ-0136, SZZG-0028, SZZG-0038, SZZG-0040,
SZZG-0069 and SZZG-0076, all of which have a multi-commit oracle. Twenty-five
scenarios designed against that axis have been added since, ten of them on
2026-09-22 (issue #35), one in each of the ten categories that had none:
SZZ-0212 (S3), SZZ-0213 (S4), SZZ-0214 (S2), SZZG-0144 (G7), SZZ-0215 (S1),
SZZG-0145 (G8), SZZG-0146 (G9), SZZG-0147 (G6), SZZ-0216 (S5) and SZZ-0217 (S7).
Two more, added the same day for issue #80, are in the tier **without being on
that axis**: SZZ-0218, where blame reaches both required commits and names a
third that is not an answer, and SZZG-0148, where blame is right about what it
names and still short of a credit threshold. Three more on 2026-09-24 shrank the
two largest pockets solved by naive rules (issue #80, proposal 3): SZZ-0219 and
SZZ-0220 in S3, where thirty-nine of forty scenarios had a one-commit oracle,
and SZZG-0149 in G4. Nine more gave every category that still rested on a
single history a second one: SZZ-0221 to SZZ-0225 for S1, S2, S5, S7 and S8,
and SZZG-0150 to SZZG-0153 for G1, G6, G7 and G8. So the
suite declares **233 control and 46 discriminating**, and every category has at
least two; the list and the reasons are in
[baselines.md](../baselines.md#the-two-tiers).

A scenario can be `discriminating` **only if its oracle names at least two
commits**, and that is a property of the declared baseline family rather than a
drafting rule: `position-k` is enumerated for the index of every answer in the
suite, so a one-commit answer is named exactly by the rule for its index, and an
empty oracle is what `abstain` predicts. `docs/baselines.md` gives the argument
and `tests/test_second_mechanism.py` checks the suite against it.

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

## 8. `meta.defeats` and `scenario_design.failure_mode`: what a scenario is built to break (issue #35)

Added 2026-09-22. A scenario may declare the **naive-rule families it is built to
make fail**:

```yaml
meta:
  tier: control
  defeats: [blame, shape]      # or [] for a control that promises nothing
scenario_design:
  failure_mode: >-
    A tool fails here when it takes plain blame's answer, the formatting
    rewrite, instead of attributing the line whitespace-insensitively.
```

- `defeats` lists families from `blame` (`blame-deleted-lines`), `shape`
  (`shape-last-toucher`) and `position` (every positional rule); a family is
  defeated when **none** of its declared baselines solves the scenario. The
  declaration is checked against the measurement by `szzbench baselines`
  (`declared_defeated_but_solved`), the way the tier is; a filtered run checks
  only the families it ran. `tier: discriminating` means defeating every
  family, and `W462` / `GW462` require the two declarations to agree.
- `failure_mode` is one sentence, "A tool fails here when it …": the concrete
  wrong step the history exercises. It is prose for the reader; the checkable
  part is `defeats`.
- Both are optional for a `control`. On 2026-09-22 the G4–G8 scenarios (82) were audited and
  declare them; the declarations were taken from the measurement (blame
  defeated in 19, shape in 28, position in the 4 `discriminating` ones), so the
  check passes by construction and guards against drift. The audit raised no
  `difficulty` above its floor: for an `exact` scenario a blame-based tool
  passes, so the failure modes the READMEs describe belong to other strategies
  (following metadata, walking the wrong parent, excluding merges), and the
  floor of §4 stands.
- A `discriminating` scenario declares both (issue #207). Eighteen declared
  neither (SZZ-0132, SZZ-0136, SZZ-0190 to SZZ-0199, SZZG-0028, SZZG-0038,
  SZZG-0040, SZZG-0118, SZZG-0119, SZZG-0120), so the drift checks had nothing
  to check them against. On 2026-10-10 they were given `defeats: [blame, shape,
  position]`, which is what the tier means, and they and the fourteen that
  declared `defeats` alone (SZZ-0212 to SZZ-0225) were given a `failure_mode`
  sentence written from the scenario. `szzbench baselines` still reports no
  contradiction, now over 124 scenarios that declare `defeats`. `W462` /
  `GW462` report a `discriminating` scenario without `defeats`; nothing checks
  `failure_mode`, which is prose.

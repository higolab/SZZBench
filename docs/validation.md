# Scenario validation

SZZBench ships three validators. All of them print one line per finding
(`[SEVERITY] CODE: message (location)`) followed by a summary, or a JSON
document with `--json`.

| command | input | exit code 1 when |
|---|---|---|
| `szzbench validate <scenario.yml>` | classic scenario | any error, or any warning with `--strict` |
| `szzbench validate-graph <scenario.graph.yml>` | graph scenario | any error, or any warning with `--strict` |
| `szzbench validate-index` | `scenarios/index.yml` and `advanced-scenarios/index.yml` | any error |

Findings have three severities. **Errors** are schema-level problems that
make a scenario unusable and always fail validation. **Warnings** point at
suspicious content and only fail validation under `--strict`. **Info** items
are never fatal.

Checks come in two groups:

* **default** checks run on every invocation;
* **lint** checks run only with `--lint`. They encode expectations about
  *good* scenarios (neutral commit messages, controlled vocabularies,
  declared ghost cases that really are ghost cases). Lint findings are
  warnings, so `--strict --lint` fails on them while plain `--strict` is
  unaffected — except the vocabulary checks (`E400`–`E402`, `GE400`–`GE404`),
  which have been errors since the suites were migrated to the controlled
  vocabularies ([decisions/vocabulary.md](decisions/vocabulary.md) §6, step 4)
  and fail `--lint` on their own.

## Flags

### `validate`

| flag | effect |
|---|---|
| `--simulate` | replay the operations in memory and run the E2xx/E3xx/W3xx oracle checks |
| `--strict` | treat warnings as failures |
| `--lint` | run the W4xx lints; the snapshot-based lints need the simulation, so `--lint` implies `--simulate` |
| `--json` | machine-readable output |

### `validate-graph`

| flag | effect |
|---|---|
| `--simulate` | replay the graph operations in memory (GE200-GE202); a scenario with commits that Git computes during generation is generated with Git in a temporary directory instead (GE203, GI203) |
| `--strict-paths` | additionally require `entity` objects on `move_entity` / `copy_entity` (GE056) |
| `--strict` | treat warnings as failures |
| `--lint` | run the GW4xx lints (static; they run only when no error was found) |
| `--json` | machine-readable output |

### `validate-index`

| flag | effect |
|---|---|
| `--scenarios-root DIR` | classic root (default `scenarios`) |
| `--advanced-scenarios-root DIR` | graph root (default `advanced-scenarios`) |
| `--json` | machine-readable output |

## Examples

```sh
# default checks, warnings fatal
szzbench validate --simulate --strict scenarios/SZZ-0006/scenario.yml
szzbench validate-graph --simulate --strict --strict-paths advanced-scenarios/SZZG-0064/scenario.graph.yml

# opt-in lints on top of the default checks
szzbench validate --strict --lint scenarios/SZZ-0053/scenario.yml
szzbench validate-graph --strict --strict-paths --lint advanced-scenarios/SZZG-0115/scenario.graph.yml

# both indexes against the scenario directories
szzbench validate-index
szzbench validate-index --json

# whole suite (lint results are informational until the scenarios are cleaned up)
for f in scenarios/SZZ-*/scenario.yml; do szzbench validate --simulate --strict "$f" >/dev/null || echo "FAIL $f"; done
for f in advanced-scenarios/SZZG-*/scenario.graph.yml; do szzbench validate-graph --simulate --strict --strict-paths "$f" >/dev/null || echo "FAIL $f"; done
```

Without the package installed, run the CLI from the repository root with
`PYTHONPATH=src python -m szzbench.cli ...`.

## Code ranges

| prefix | suite | meaning |
|---|---|---|
| `E`/`W` | classic (`scenario.yml`) | error / warning |
| `GE`/`GW` | graph (`scenario.graph.yml`) | error / warning |
| `IE`/`IW` | index (`index.yml`) | error / warning |

Codes are stable: a code is never reused for a different check. New checks
continue the numbering of their group; the `x4xx` block is reserved for
`--lint` (W4xx / GW4xx warnings, and E4xx / GE4xx for the lint checks that
became errors — the code keeps its number when its severity changes, so
`W400` became `E400`).

## Classic suite (`validate`)

### Default checks

| code | severity | meaning |
|---|---|---|
| E000 | error | scenario file cannot be read, or is not UTF-8 (the message gives the first byte that is not, and its offset; [issue #149](https://github.com/higolab/SZZBench/issues/149)) |
| E001 | error | YAML parse error (duplicate keys are rejected) |
| E002 | error | the YAML root is not a mapping |
| E003 | error | the file is a graph scenario: its `schema_version` is a graph schema (the rule of GE001), or it has none and the file is named `scenario.graph.yml` (GW014). `validate` reports it before any other check, and `generate` and `verify` refuse the file too. The message names the graph command to run instead (`validate-graph`, `generate-graph`, `verify-graph`) ([issue #119](https://github.com/higolab/SZZBench/issues/119)) |
| E010 | error | a required field is missing or has the wrong type (`schema_version`, `meta`, `repository`, `commits`, `bugs`, `meta.id/title/category/factors`, `repository.name/default_branch/language`, commit `id/message/operations`, bug `id/bug_fixing_commit/bug_introducing_commits`) |
| E011 | error | `commits` is empty |
| E020 | error | duplicate commit id |
| E030 | error | unknown commit `role` (see `ALLOWED_ROLES`) |
| E040 | error | unknown operation type |
| E041 | error | `operation.type` missing, or a required operation field missing |
| E050 | error | operation path is not a repository-relative POSIX path, names separated by `/`. It is refused when it is absolute; starts with a drive prefix (`C:`); contains a control character (U+0000–U+001F or U+007F, a NUL byte included), a backslash, an empty component (`a//b`, a trailing `/`), a `.` or `..` component, or a component of only whitespace; or names the repository's own `.git` in any spelling a file system resolves to it — any letter case (`.GIT`), the NTFS 8.3 short name `git~1`, either of them followed by dots or spaces (`.git.`, `git~1 `), by an alternate data stream (`.git::$INDEX_ALLOCATION`) or by a backslash, or with code points HFS+ ignores. The `.git` spellings are the names Git refuses as tree entries with `core.protectNTFS` and `core.protectHFS`. The message names the rule the path breaks. The rule is read from the string, so the verdict is the same on every platform: it used to be `pathlib.Path`'s, which on Windows reads `..\escape.txt` as `..` and `C:\x.txt` as absolute and elsewhere reads each as one file name; a NUL byte passed and ended `generate` in a traceback, and `src/Dir/` was written as the file `src/Dir` ([issue #136](https://github.com/higolab/SZZBench/issues/136)). On a case-insensitive file system `.GIT/config` used to pass and overwrite the generated repository's configuration ([issue #135](https://github.com/higolab/SZZBench/issues/135)) |
| E060 | error | `bug_fixing_commit` refers to an unknown commit |
| E061 | error | a `bug_introducing_commits` entry refers to an unknown commit |
| E062 | error | `fault.commit` refers to an unknown commit |
| E063 | error | `fix.commit` refers to an unknown commit |
| E070 | error | a BIC does not precede the BFC in the linear history |
| E080 | error | `fault.commit` is not listed in `bug_introducing_commits` |
| E081 | error | `fix.commit` differs from `bug_fixing_commit` |
| E082 | error | `bug_introducing_commits` is empty |
| E083 | error | duplicate entries in `bug_introducing_commits` |
| E900 | error | operation is recognised but not supported by the classic generator |
| W001 | warning | `meta.id` differs from the scenario directory name |
| W090 | warning | the BFC's `role` is not `bug_fixing` |
| W091 | warning | a BIC's `role` is not `bug_introducing` |

With `--simulate`:

| code | severity | meaning |
|---|---|---|
| E2XX | error | an operation failed during in-memory replay (message carries the cause) |
| E250 | error | a commit produces no change in the simulated text. An operation whose `encoding` adds or removes the BOM *is* a change (the simulator stores a BOM as a leading U+FEFF and applies the codec on read and write, for `write_file` and `replace` alike), so a BOM-only re-save such as SZZ-0206's `c2` passes |
| E300 | error | `fault.file` does not exist at `fault.commit` |
| E301 | error | `fault.statement` missing, or absent at `fault.commit` |
| W301 | warning | `fault.statement` occurs more than once at `fault.commit`. Silenced by a `meta.factors` entry matching `duplicate`, `ambiguous`, `overload` or `repetitive`, for scenarios whose point is the duplication |
| E310 | error | `fix.file` does not exist at `fix.commit` |
| E311 | error | fix statement missing, or absent at `fix.commit`. One of `fix.statement`, `fix.added_statement` or `fix.removed_statement` is required |
| E312 | error | `fix.removed_statement` is still present at `fix.commit`; a fix declared as a deletion must actually have removed it |
| E313 | error | `fix.removed_statement` is not present in `fix.file` immediately before `fix.commit`; the declared text was never there, so the fix removed nothing. Without this, a `removed_statement` naming text that occurs in no snapshot is trivially "absent afterwards" and passes |
| W320 | warning | `fault.file`/`fault.statement` not present immediately before the BFC. The statement case is silenced by a `meta.factors` entry matching `after-bic`, `rewrite`, `refactor`, `format`, `whitespace`, `rename`, `move`, `inline` or `extract`, for scenarios whose point is that the fault line was rewritten between BIC and BFC |
| W330 | warning | fix statement already present immediately before the BFC. Silenced by the same duplication factors as W301, and by declaring `fix.removed_statement` — a fix that only deletes adds no text that could be "already present" |
| W350 | warning | omission bug that also carries a `fault.statement` |
| E351 | error | omission bug without `fault.missing_statement` |

### Lints (`--lint`)

| code | severity | meaning | suppressed by |
|---|---|---|---|
| E400 | error | a factor is a schema key or operation name (`expected_szz`, `faults`, `write_file`, `replace`, `edit`, `drop`, ...; see `RESERVED_FACTOR_WORDS`). Was `W400` until 2026-09-22 | – |
| E401 | error | `meta.factors` is empty (was `W401`) | – |
| E402 | error | factors mix hyphen and underscore styles within one scenario (was `W402`) | – |
The W41x / GW41x lints implement the leakage policy in
[decisions/oracle-leakage.md](decisions/oracle-leakage.md); `tests/test_no_oracle_leakage.py` enforces it over the shipped scenarios.

| W410 | warning | a commit that is **not** the BFC has a message disclosing its role: `introduce ... bug` (with hyphenated words in between, e.g. `introduce context-sensitive bug`), `bug-introducing`, `with ... bug`, `buggy`, `faulty`, `faulty statement/line/code/commit`, `BIC`, `BFC`, `distractor`, `intermediate change`, `initial state`, `noise`, `unrelated`, `replay...`, `reintroduc...` (case-insensitive). Natural "fix" wording in the BFC is never flagged. | – |
| W411 | warning | a message exposes a logical id: one of the scenario's own commit ids as a standalone word, wherever it appears (`c1: ...`, `WI-001 c2: ...`, `suspected c0`), or an id-shaped token used as a prefix (`Rel1:`). Hyphenated issue and work-item ids (`ISSUE-482`, `PAY-314`, `WI-001`) are legitimate and are not flagged. | – |
| W412 | warning | text written into the repository (`write_file.content`, `replace.new`, `insert_after.content`) matches the W410 role wording | – |
| W413 | warning | some author's set of commits equals the resolved default oracle and the oracle has two or more commits: the cheap baseline "report every commit by this author" returns the oracle by coincidence of the generator's author rotation (issue #43). Give the required commits distinct explicit `author`s. The oracle is resolved as the evaluator resolves it; the history is the one the generated repository will have — every commit with its explicit or deterministic default author, compared as Git records it (`name <email>`, so two spellings of one identity are one author), plus the commits `commit_generator` expands (`<owner>.g<N>`, attributed by the generator's rotation), and restricted to what a ref still reaches once `graph.ref_lifecycle` has run (a deleted branch's commits drop out unless a kept branch, a tag or HEAD reaches them; a tag may point into a generated chain, and each generated commit counts on its own reachability, not its owner's) — the history the author baseline sees through `git log --all` |
| I413 | info | the same coincidence for a one-commit oracle — reported, not repaired: a one-commit oracle is solved by many cheap rules anyway |
| W455 | warning | the sibling README disagrees with the scenario: its generated header is missing, differs from what the scenario renders (the message quotes the first differing line), or a hand-written `## Factors` / `## Source` copy is present. `szzbench readme --write` regenerates it ([scenario-readme.md](scenario-readme.md)) | – |
| W460 | warning | `meta.tier` is missing or is not one of `control` / `discriminating` (see [decisions/vocabulary.md](decisions/vocabulary.md)) | – |
| W461 | warning | `meta.difficulty` is missing or is not one of `easy` / `medium` / `hard`; the floor a scenario may not go below is measured by `szzbench coverage` ([decisions/vocabulary.md](decisions/vocabulary.md) §4) | – |
| W462 | warning | `meta.defeats` (optional) is not a list of distinct family names from `blame` / `shape` / `position`, or a `discriminating` scenario does not list all three ([decisions/vocabulary.md](decisions/vocabulary.md) §8); `szzbench baselines` checks the declaration against the measurement | – |
| W420 | warning | ghost invariant: the BFC deletes or modifies an existing line although the scenario is declared as an addition-only fix. Declared by a factor in {`addition-only-fix`, `ghost-fix`, `add_only_fix`} (applies to every bug) or, per bug, by `fault.change_type: omission` together with `fix.fix_type` in {`line_addition`, `file_creation`} | a factor matching `tangled\|noise\|distractor\|adjacent-edit`, which declares that the fix deliberately carries unrelated deleted lines |
| W421 | warning | ghost invariant: a BIC adds lines although the scenario is declared as a deletion-only BIC (factor `deletion-only-bic` or `line-deletion-bic`) | – |
| W430 | warning | an intermediate non-BIC commit between `fault.commit` and the BFC removes the fault statement from `fault.file` | a factor matching `after-bic\|rewrite\|refactor\|format\|whitespace\|rename\|move\|inline\|extract` |
| W431 | warning | the BFC deletes or modifies lines whose most recent author (difflib line tracking over the simulated snapshots) is not a BIC of the bug | a factor matching `tangled\|distractor\|candidate`, `noise\|adjacent-edit` (the BFC carries unrelated or cosmetic edits), or `root-cause\|config\|caller-update\|multi-line-statement\|cross-file` (the repair legitimately sits away from the BIC: the root cause is in another file, the BIC is a configuration or dependency change, the fix updates call sites, or the faulty expression spans lines from several commits) |

W420/W421/W430/W431 compare the simulated snapshots before and after a commit
with `difflib.SequenceMatcher` on whole lines, i.e. a re-indented line counts
as one deleted and one added line, like `git blame` without `-w`.

## Graph suite (`validate-graph`)

### Default checks

| code | severity | meaning |
|---|---|---|
| GE001 | error | `schema_version` is not a graph schema (`graph-...`) |
| GE010 | error | missing top-level field |
| GE011 | error | `meta` is not an object |
| GE012 | error | `meta.id` missing |
| GE013 | error | `meta.id` is not `SZZG-XXXX` |
| GW014 | warning | file is not named `scenario.graph.yml` |
| GW015 | warning | `meta.title` / `meta.category` / `meta.factors` missing |
| GE016 | error | `meta.factors` is not a list |
| GE020 | error | `repository` is not an object |
| GW021 | warning | `repository.name` / `repository.default_branch` missing |
| GE030 | error | `commits` is not a list |
| GE031 | error | `commits` is empty |
| GE032 | error | a commit is not an object |
| GE033 | error | `commit.id` missing or empty |
| GE034 | error | duplicate commit id |
| GE035 | error | `commit.branch` is not a string |
| GE036 | error | `commit.parents` is not a list |
| GE037 | error | a parent id is not a string |
| GE038 | error | a parent appears later in the file (topological order required) |
| GE039 | error | unknown parent commit |
| GW040 | warning | `role: merge` with fewer than two parents |
| GW041 | warning | several parents but a role that is not merge-like |
| GE042 | error | `cherry_pick_of` / `backport_of` is not a string |
| GE043 | error | `cherry_pick_of` / `backport_of` refers to an unknown or later commit |
| GE044 | error | `commit.operations` is not a list |
| GW045 | warning | non-merge commit without operations and without `allow_empty`. Not reported for a commit that declares `revert_of`, `cherry_pick_of` or `backport_of`: with no operations, `git revert` / `git cherry-pick` supplies its content (generator-options §3), so it is not empty and marking it `allow_empty` would be false |
| **GE046** | error | `rebase_of` (string or list of strings), `squashes` (list of strings) or `revert_of` (string) has the wrong type |
| **GE047** | error | `rebase_of` / `squashes` / `revert_of` refers to an unknown, later, or the same commit (the GE043 rule for rewrite metadata; catches SZZG-0067's `rebase_of: f1`) |
| GE048 | error | a commit other than the first declares no parents (`parents: []`, or no `parents` key, e.g. a misspelt `parent:`). Only the first commit is a root: a second one used to be generated as a child of whatever the generator had last checked out, while `commit-map.json` recorded no parents and `verify-graph` did not look. The message names a near-miss key when there is one ([issue #134](https://github.com/higolab/SZZBench/issues/134)) |
| GE050 | error | an operation is not an object |
| GE051 | error | `operation.type` missing |
| GE052 | error | unknown graph operation type |
| GE053 | error | required operation field missing |
| GE054 | error | operation path is not a repository-relative POSIX path (the rule of E050: a drive prefix, a backslash, a control character, an empty, `.`, `..` or whitespace-only component, and `.git` in any spelling are refused) |
| GE055 | error | a path field is not a string |
| GE056 | error | (`--strict-paths`) `move_entity` / `copy_entity` without an `entity` object |
| GE057 | error | a `chmod` `mode` that is not a quoted string of 3 or 4 octal digits (`'755'`). YAML reads an unquoted `0755` as the integer 493, which used to reach generation and end in a traceback ([issue #172](https://github.com/higolab/SZZBench/issues/172)) |
| GE058 | error | a `write_binary_file` `content_base64` that is not a string or does not decode as base64. ASCII whitespace is ignored; any other character outside the alphabet, a non-ASCII one or a no-break space included, and wrong padding are not. Validation, `--simulate` and generation read the value the same way. Generation used to end in a traceback, or to drop the characters outside the alphabet and write a shorter file ([issue #172](https://github.com/higolab/SZZBench/issues/172)) |
| GE059 | error | a `write_generated_text_file` `lines` that is not a non-negative integer ([issue #172](https://github.com/higolab/SZZBench/issues/172)) |
| GE080 | error | `bugs` is not a list |
| GE081 | error | a bug is not an object |
| GE082 | error | `bug.id` missing |
| GE083 | error | duplicate bug id |
| GE084 | error | bug without `bug_introducing_commits` (missing or empty; GI086 instead when `expect_no_bic` is declared), or with one that is not a list, which is an error even under `expect_no_bic`. A non-list used to raise or, as a string, to count as one commit per character ([issue #127](https://github.com/higolab/SZZBench/issues/127)) |
| GE085 | error | bug without `bug_fixing_commits` / `bug_fixing_commit` |
| GE090 | error | BIC/BFC entry `role` is not a string |
| GE091 | error | BIC/BFC entry is neither a string nor an object |
| GE092 | error | BIC/BFC entry without commit id |
| GE093 | error | BIC/BFC entry refers to an unknown commit |
| GE100 | error | fault/fix location without `commit` |
| GE101 | error | fault/fix location refers to an unknown commit |
| GE102 | error | fault/fix `file` is not a repository-relative POSIX path (the rule of E050) |
| GE103 | error | fault/fix `file` is not a string |
| GE104 | error | fault/fix location requires a statement |
| GE105 | error | fault/fix `entity` is not an object |
| GW120 | warning | `expected_szz` missing |
| GE120 | error | `expected_szz` is not an object |
| GE121 | error | `acceptable_related` refers to an unknown commit, in `expected_szz.commit_level` or in any `evaluation_variants[].commit_level` |
| GE122 | error | `expected_szz.evaluation_variants` is not a list, or one of its entries is not an object with a non-empty string `name`. The evaluator selects a variant by its name; until [issue #127](https://github.com/higolab/SZZBench/issues/127) these passed without `--lint` and raised with it |
| GW123 | warning | unknown `evaluation_policy` in `expected_szz.commit_level` **or in any `evaluation_variants[].commit_level`**. The vocabulary is `szzbench.policies.SUPPORTED_EVALUATION_POLICIES` = {`exact_set`, `direct_only`, `reintroduction_direct`, `partial_credit`, `top_k`, `relaxed_with_related`, `relaxed_with_credit`}, identical to the evaluator's set (a test enforces this). |
| GE124 | error | a commit list (`required`, `relevant`, `related_origins`, `related_but_not_correct`, `acceptable_related`) of `expected_szz.commit_level` or of any `evaluation_variants[].commit_level` is not a list. Variants were checked for `required` only, and `acceptable_related` not at all, until the review of PR #124: GW130 hands both oracles to the evaluator, which reads every list |
| GE125 | error | a commit list entry is not a commit id |
| GE126 | error | a commit list entry refers to an unknown commit |
| GE127 | error | `expected_szz.branch_level` is not a non-empty object, or an entry is not an object with `bfc` (a commit id) and `required` (a list; a blank `required:` is rejected, `[]` is an intentionally empty answer) ([evaluation-policies.md](evaluation-policies.md) §1.5) |
| GE128 | error | a `branch_level` entry's `bfc` refers to an unknown commit |
| GE129 | error | `expected_szz.default_variant` is present but names no declared evaluation variant, matched the way the evaluator matches names (case and `-`/`_` ignored). A blank `default_variant:` counts: YAML reads it as null. The evaluator would ignore it and score `commit_level`, with a note at every evaluation for an unknown name and none for a null; omit `default_variant` to make `commit_level` the default ([evaluation-policies.md](evaluation-policies.md) §1.3) |
| GW130 | warning | a commit-level oracle the evaluator would have to infer: the oracle scored by default (`commit_level`, or the evaluation variant `default_variant` names), or any evaluation variant, declares neither a non-empty `required` nor `expect_no_bic: true`. The evaluator then takes `required` from `bugs[]` and notes it at every evaluation ([evaluation-policies.md](evaluation-policies.md) §1.4). Asked of the evaluator, as GE129 is ([issue #118](https://github.com/higolab/SZZBench/issues/118)) |
| GE140 | error | `work_items` / `issues` / `developer_hints` is not a list |
| GE141 | error | a developer hint refers to an unknown commit |
| GE142 | error | a developer hint references an unknown commit |
| GE150 | error | the commit graph contains a cycle |

With `--simulate`:

| code | severity | meaning |
|---|---|---|
| GE200 | error | the parent snapshot cannot be prepared (unsimulated parent, merge conflict) |
| GE201 | error | an operation failed during in-memory replay |
| GE202 | error | a non-merge commit without `allow_empty` would be empty |
| GE203 | error | generating the scenario with Git in a temporary directory failed; the message and location name the commit that failed (an unresolved conflict, a revert or cherry-pick that changes nothing, an operation that no longer applies) |
| GI203 | info | the scenario was simulated by generating it with Git; the message lists the commits Git computes |

The in-memory replay models file operations. What the generator lets Git
compute -- merge commits, `revert_of` performed by `git revert` (no operations,
or `apply_revert: true`), `cherry_pick_of` / `backport_of` without operations,
the `apply_patch_from` and `apply_squash` operations, and conflict
`resolution` -- it approximated file by file or not at all. So a scenario with
any of these is simulated by the generator itself, in a temporary directory,
without verification (issue #94); every other scenario keeps the in-memory
replay and its operation-level locations. Until 2026-09-29 the replay was used
for all of them, and nine shipped scenarios that generate and verify failed
`--simulate` with 17 errors. `graph_simulator.git_performed_features` holds the
list, with the generator's own conditions.

### Lints (`--lint`)

| code | severity | meaning |
|---|---|---|
| GE400 | error | a factor is a schema key or operation name (same list as E400; was `GW400` until 2026-09-22) |
| GE401 | error | `meta.factors` is empty (was `GW401`) |
| GE402 | error | factors mix hyphen and underscore styles (was `GW402`) |
| GE403 | error | a BIC entry role is a non-canonical spelling; canonical roles are {`direct`, `origin`, `contributing`, `reintroducing`}. Consumers normalize known aliases (the evaluator/verifier role normalization of #27 does), but a scenario declares the canonical spelling (was `GW403`) |
| GE404 | error | a BFC entry role is not in {`complete_fix`, `partial_fix`} (was `GW404`) |
| GW460 | warning | `meta.tier` is missing or outside the vocabulary (same rule as W460) |
| GW461 | warning | `meta.difficulty` is missing or outside `easy` / `medium` / `hard` (same rule as W461; `advanced` is retired) |
| GW462 | warning | `meta.defeats` is malformed or disagrees with a `discriminating` tier (same rule as W462) |
| GW410 | warning | a commit that is not a BFC (of any bug) has a role-disclosing message (same pattern as W410) |
| GW411 | warning | a message exposes a logical id (same rule as W411) |
| GW412 | warning | written text (`write_file.content`, `replace.new`, `insert_after.content`) contains role wording |
| GW413 | warning | some author's set of commits equals the resolved default oracle of two or more commits (same rule as W413) |
| GI413 | info | the same coincidence for a one-commit oracle (same rule as I413) |
| GW440 | warning | `move_entity` / `copy_entity`: file-level approximation, the whole source file is copied under a marker header |
| ~~GW441~~ | retired | `commit_generator` now expands into real commits (see `docs/generator-options.md`) |
| ~~GW442~~ | retired | `chmod` is now recorded: the generator enables `core.filemode` for scenarios that use it |
| GW443 | warning | `apply_patch`: recognised by the schema but not implemented, generation fails |
| GW450 | warning | a BIC whose role contains `origin` is named in none of `expected_szz` lists (`required`, `acceptable_related`, `related_origins`, `related_but_not_correct`, `relevant`) of `commit_level` or of any evaluation variant |
| GW451 | warning | an origin BIC that the **default** variant does not list under `related_origins`, so predicting it is a plain false positive instead of a recognised origin ([decisions/origin-direct-contract.md](decisions/origin-direct-contract.md) D2) |
| GW452 | warning | a scenario with an origin BIC and no `origin-aware` evaluation variant, so a tool that reports origins as context cannot be scored (D3) |
| GW453 | warning | an `origin-aware` variant that does not accept the origin, so the variant's name promises what its policy does not deliver (D3) |
| GW454 | warning | the sibling README's `## Expected history` block contradicts the scenario: a commit's operation list differs from `commits[].operations`, or the block names a commit the scenario does not define. Only the parenthesised operation list is compared, because only that part is mechanically derivable; READMEs that describe the history in prose have no such block and are not linted |
| GW455 | warning | the sibling README's generated header is missing, stale, or duplicated by a hand-written `## Factors` / `## Source` copy (same rule as W455; [scenario-readme.md](scenario-readme.md)) |
| GW470 | warning | an `issues[]` entry names a `document` that no commit writes with `write_file`, or has `reported_at` without a `document` — the report would not be visible to a tool ([decisions/tool-visible-context.md](decisions/tool-visible-context.md)) |
| GW471 | warning | the issue document has no `Reported: <timestamp>` line, its value is not an ISO 8601 timestamp, or it names a different instant from `issues[].reported_at`. Both values are normalised through the same parser and compared as instants, so an unquoted YAML timestamp (a `datetime`) and a different UTC offset are handled; `reported_at` and the document are copies of each other and must agree |
| GW472 | warning | `issues[].reported_at` is neither an ISO 8601 string nor the `datetime` PyYAML makes of an unquoted one — it is reported rather than silently skipped |

Ghost invariants (the graph counterparts of W420/W421) are **not**
implemented: `graph_simulator.simulate_graph_scenario` does not expose
per-commit snapshots, so there is nothing to diff. No graph scenario
currently declares a ghost class.

Not resolved as commit references: `interactive_rebase` (its values are
actions such as `squash` or `reorder`) and `reverts` (free-form: commit ids,
`part_of_c3`, or objects).

### Generated-repository checks (`verify-graph`, also run by `generate-graph`)

| code | level | condition |
|---|---|---|
| GE603 | error | the repository path is not a Git repository (missing, or without `.git`); the classic `verify` reports the same as E603. Verification used to end in a `FileNotFoundError` traceback when `--commit-map` named an existing map ([issue #166](https://github.com/higolab/SZZBench/issues/166)) |
| GE627 | error | a commit's parents in the repository are not the declared ones, in order (for a commit that owns `commit_generator` operations, the first parent is the last generated commit). Since issue #134 this includes a commit declared without parents: it must have none |
| GE630 | error | a commit is committed **before one of its parents**. A scenario that pins some timestamps and leaves the rest to the generator can otherwise invert its own history, which changes what date-based candidate filters and recency heuristics see (issue #9, PR #34 re-review) |
| GW631 | warning | a commit's author date is **after** its committer date. An author date *before* the committer date is the normal signature of a rebase and is not flagged |
| GW632 | warning | the commit-date check could not run (Git failed, or a timestamp was unreadable) |

Both comparisons use Git's epoch seconds (`%ct` / `%at`), not the ISO strings: `%cI` / `%aI` keep each timestamp's UTC offset, so `2024-01-01T10:00:00+09:00` sorts after `2024-01-01T02:00:00Z` as text although it is an hour earlier. The ISO forms appear only in the finding message.

## Index (`validate-index`)

For each of `scenarios/index.yml` (scenario file `scenario.yml`) and
`advanced-scenarios/index.yml` (`scenario.graph.yml`). Locations are prefixed
with the index path.

| code | severity | meaning |
|---|---|---|
| IE001 | error | the index cannot be read or parsed |
| IE002 | error | `scenarios` is not a list |
| IE003 | error | the scenario root is not a directory |
| IE010 | error | `scenario_count` (when present) differs from the number of entries |
| IE020 | error | an entry is not an object with a string `id` |
| IE021 | error | duplicate entry id |
| IE022 | error | the entry has no `<root>/<id>/<scenario file>` |
| IW023 | warning | the entry's `path` differs from `<root>/<id>/<scenario file>` |
| IE030 | error | a scenario directory under the root has no index entry |
| IE040 | error | the entry id differs from the scenario's `meta.id` |
| IE041 | error | the entry title differs from the scenario's `meta.title` |
| IE043 | error | an index entry's `factors` differ from the scenario's `meta.factors`; the index repeats a field that changes with the scenario, which is how it drifted before ([issue #19](https://github.com/higolab/SZZBench/issues/19)) |
| IE044 | error | an index entry's `factors`, or the scenario's `meta.factors`, is not a list; neither side is validated before IE043 compares them |
| IE045 | error | an index entry's `status` differs from the scenario's `meta.status` |
| IE046 | error | an index entry's `slug`, `category`, `category_code` or `difficulty` differs from the scenario's `meta` value. These four are copied into the index like `title`, `status` and `factors`, and were the last mirrored fields nothing checked |
| IE047 | error | an index entry, or a directory under the scenario root, uses a retired id: one in the first column of the table in `docs/retired-ids.md`, read from the `docs/` beside the root. A withdrawn scenario's id is never reused ([issue #112](https://github.com/higolab/SZZBench/issues/112)) |
| IE042 | error | the scenario file of an entry cannot be loaded |

## Verifier findings that depend on a declaration

`szzbench verify` / `verify-graph` blame the fault statement at the BFC's parent as a
basic check. When that statement is not present there, the outcome depends on what the
scenario declares:

| code | level | meaning |
|---|---|---|
| W700 / GW701 | warning | `fault.statement` is not present in the BFC parent, so basic blame is unavailable — and the scenario does not say why |
| I701 / GI701 | info | the same, but `meta.factors` declares a rewrite of the fault line (`after-bic\|rewrite\|refactor\|format\|whitespace\|rename\|move\|inline\|extract`, the vocabulary W320 honours): blame being unavailable is the scenario's point (SZZ-0081–0083, SZZG-0130, SZZG-0132) |
| I700 / GI703 | info | basic blame reaches an expected BIC |
| W700 / GW703 | warning | basic blame reaches a commit that is not an expected BIC |
| GW700 / GW702 | warning | the blame check could not run (file unreadable, `git blame` failed) |


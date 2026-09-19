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
  declared ghost cases that really are ghost cases). Every lint finding is a
  warning, so `--strict --lint` fails on them while plain `--strict` is
  unaffected.

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
| `--simulate` | replay the graph operations in memory (GE2xx) |
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
continue the numbering of their group; the `x4xx` block (W4xx, GW4xx) is
reserved for `--lint`.

## Classic suite (`validate`)

### Default checks

| code | severity | meaning |
|---|---|---|
| E000 | error | scenario file cannot be read |
| E001 | error | YAML parse error (duplicate keys are rejected) |
| E002 | error | the YAML root is not a mapping |
| E010 | error | a required field is missing or has the wrong type (`schema_version`, `meta`, `repository`, `commits`, `bugs`, `meta.id/title/category/factors`, `repository.name/default_branch/language`, commit `id/message/operations`, bug `id/bug_fixing_commit/bug_introducing_commits`) |
| E011 | error | `commits` is empty |
| E020 | error | duplicate commit id |
| E030 | error | unknown commit `role` (see `ALLOWED_ROLES`) |
| E040 | error | unknown operation type |
| E041 | error | `operation.type` missing, or a required operation field missing |
| E050 | error | operation path is not a safe repository-relative path |
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
| E250 | error | a commit produces no change |
| E300 | error | `fault.file` does not exist at `fault.commit` |
| E301 | error | `fault.statement` missing, or absent at `fault.commit` |
| W301 | warning | `fault.statement` occurs more than once at `fault.commit` |
| E310 | error | `fix.file` does not exist at `fix.commit` |
| E311 | error | fix statement missing, or absent at `fix.commit` |
| W320 | warning | `fault.file`/`fault.statement` not present immediately before the BFC |
| W330 | warning | fix statement already present immediately before the BFC |
| W350 | warning | omission bug that also carries a `fault.statement` |
| E351 | error | omission bug without `fault.missing_statement` |

### Lints (`--lint`)

| code | severity | meaning | suppressed by |
|---|---|---|---|
| W400 | warning | a factor is a schema key or operation name (`expected_szz`, `faults`, `write_file`, `replace`, `edit`, `drop`, ...; see `RESERVED_FACTOR_WORDS`) | – |
| W401 | warning | `meta.factors` is empty | – |
| W402 | warning | factors mix hyphen and underscore styles within one scenario | – |
The W41x / GW41x lints implement the leakage policy in
[decisions/oracle-leakage.md](decisions/oracle-leakage.md); `tests/test_no_oracle_leakage.py` enforces it over the shipped scenarios.

| W410 | warning | a commit that is **not** the BFC has a message disclosing its role: `introduce ... bug` (with hyphenated words in between, e.g. `introduce context-sensitive bug`), `bug-introducing`, `with ... bug`, `buggy`, `faulty`, `faulty statement/line/code/commit`, `BIC`, `BFC`, `distractor`, `intermediate change`, `initial state`, `noise`, `unrelated`, `replay...`, `reintroduc...` (case-insensitive). Natural "fix" wording in the BFC is never flagged. | – |
| W411 | warning | a message exposes a logical id: one of the scenario's own commit ids as a standalone word, wherever it appears (`c1: ...`, `WI-001 c2: ...`, `suspected c0`), or an id-shaped token used as a prefix (`Rel1:`). Hyphenated issue and work-item ids (`ISSUE-482`, `PAY-314`, `WI-001`) are legitimate and are not flagged. | – |
| W412 | warning | text written into the repository (`write_file.content`, `replace.new`, `insert_after.content`) matches the W410 role wording | – |
| W460 | warning | `meta.tier` is missing or is not one of `control` / `discriminating` (see [decisions/vocabulary.md](decisions/vocabulary.md)) | – |
| W420 | warning | ghost invariant: the BFC deletes or modifies an existing line although the scenario is declared as an addition-only fix. Declared by a factor in {`addition-only-fix`, `ghost-fix`, `add_only_fix`} (applies to every bug) or, per bug, by `fault.change_type: omission` together with `fix.fix_type` in {`line_addition`, `file_creation`} | a factor matching `tangled\|noise\|distractor\|adjacent-edit`, which declares that the fix deliberately carries unrelated deleted lines |
| W421 | warning | ghost invariant: a BIC adds lines although the scenario is declared as a deletion-only BIC (factor `deletion-only-bic` or `line-deletion-bic`) | – |
| W430 | warning | an intermediate non-BIC commit between `fault.commit` and the BFC removes the fault statement from `fault.file` | a factor matching `after-bic\|rewrite\|refactor\|format\|whitespace\|rename\|move\|inline\|extract` |
| W431 | warning | the BFC deletes or modifies lines whose most recent author (difflib line tracking over the simulated snapshots) is not a BIC of the bug | a factor matching `tangled\|distractor\|candidate` |

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
| GW045 | warning | non-merge commit without operations and without `allow_empty` |
| **GE046** | error | `rebase_of` (string or list of strings), `squashes` (list of strings) or `revert_of` (string) has the wrong type |
| **GE047** | error | `rebase_of` / `squashes` / `revert_of` refers to an unknown, later, or the same commit (the GE043 rule for rewrite metadata; catches SZZG-0067's `rebase_of: f1`) |
| GE050 | error | an operation is not an object |
| GE051 | error | `operation.type` missing |
| GE052 | error | unknown graph operation type |
| GE053 | error | required operation field missing |
| GE054 | error | operation path is not a safe repository-relative path |
| GE055 | error | a path field is not a string |
| GE056 | error | (`--strict-paths`) `move_entity` / `copy_entity` without an `entity` object |
| GE080 | error | `bugs` is not a list |
| GE081 | error | a bug is not an object |
| GE082 | error | `bug.id` missing |
| GE083 | error | duplicate bug id |
| GE084 | error | bug without `bug_introducing_commits` |
| GE085 | error | bug without `bug_fixing_commits` / `bug_fixing_commit` |
| GE090 | error | BIC/BFC entry `role` is not a string |
| GE091 | error | BIC/BFC entry is neither a string nor an object |
| GE092 | error | BIC/BFC entry without commit id |
| GE093 | error | BIC/BFC entry refers to an unknown commit |
| GE100 | error | fault/fix location without `commit` |
| GE101 | error | fault/fix location refers to an unknown commit |
| GE102 | error | fault/fix `file` is not a safe repository-relative path |
| GE103 | error | fault/fix `file` is not a string |
| GE104 | error | fault/fix location requires a statement |
| GE105 | error | fault/fix `entity` is not an object |
| GW120 | warning | `expected_szz` missing |
| GE120 | error | `expected_szz` is not an object |
| GE121 | error | `acceptable_related` refers to an unknown commit |
| GE122 | error | an evaluation variant is not an object |
| GW123 | warning | unknown `evaluation_policy` in `expected_szz.commit_level` **or in any `evaluation_variants[].commit_level`**. The vocabulary is `szzbench.policies.SUPPORTED_EVALUATION_POLICIES` = {`exact_set`, `direct_only`, `reintroduction_direct`, `partial_credit`, `top_k`, `relaxed_with_related`, `relaxed_with_credit`}, identical to the evaluator's set (a test enforces this). |
| GE124 | error | a commit list (`required`, `relevant`, `related_origins`, `related_but_not_correct`) is not a list |
| GE125 | error | a commit list entry is not a commit id |
| GE126 | error | a commit list entry refers to an unknown commit |
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

### Lints (`--lint`)

| code | severity | meaning |
|---|---|---|
| GW400 | warning | a factor is a schema key or operation name (same list as W400) |
| GW401 | warning | `meta.factors` is empty |
| GW402 | warning | factors mix hyphen and underscore styles |
| GW403 | warning | a BIC entry role is a non-canonical spelling; canonical roles are {`direct`, `origin`, `contributing`, `reintroducing`}. Consumers may normalize known aliases (the evaluator/verifier role normalization of #27 does), but the canonical spelling is recommended |
| GW404 | warning | a BFC entry role is not in {`complete_fix`, `partial_fix`} |
| GW460 | warning | `meta.tier` is missing or outside the vocabulary (same rule as W460) |
| GW410 | warning | a commit that is not a BFC (of any bug) has a role-disclosing message (same pattern as W410) |
| GW411 | warning | a message exposes a logical id (same rule as W411) |
| GW412 | warning | written text (`write_file.content`, `replace.new`, `insert_after.content`) contains role wording |
| GW440 | warning | `move_entity` / `copy_entity`: file-level approximation, the whole source file is copied under a marker header |
| ~~GW441~~ | retired | `commit_generator` now expands into real commits (see `docs/generator-options.md`) |
| ~~GW442~~ | retired | `chmod` is now recorded: the generator enables `core.filemode` for scenarios that use it |
| GW443 | warning | `apply_patch`: recognised by the schema but not implemented, generation fails |
| GW450 | warning | a BIC whose role contains `origin` is named in none of `expected_szz` lists (`required`, `acceptable_related`, `related_origins`, `related_but_not_correct`, `relevant`) of `commit_level` or of any evaluation variant |
| GW451 | warning | an origin BIC that the **default** variant does not list under `related_origins`, so predicting it is a plain false positive instead of a recognised origin ([decisions/origin-direct-contract.md](decisions/origin-direct-contract.md) D2) |
| GW452 | warning | a scenario with an origin BIC and no `origin-aware` evaluation variant, so a tool that reports origins as context cannot be scored (D3) |
| GW453 | warning | an `origin-aware` variant that does not accept the origin, so the variant's name promises what its policy does not deliver (D3) |
| GW454 | warning | the sibling README's `## Expected history` block contradicts the scenario: a commit's operation list differs from `commits[].operations`, or the block names a commit the scenario does not define. Only the parenthesised operation list is compared, because only that part is mechanically derivable; READMEs that describe the history in prose have no such block and are not linted |

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
| IE043 | error | an index entry's `factors` differ from the scenario's `meta.factors`; the index repeats a field that changes with the scenario, which is how it drifted before ([issue #19](https://github.com/YoshikiHigo/SZZBench/issues/19)) |
| IE044 | error | an index entry's `factors`, or the scenario's `meta.factors`, is not a list; neither side is validated before IE043 compares them |
| IE045 | error | an index entry's `status` differs from the scenario's `meta.status` |
| IE042 | error | the scenario file of an entry cannot be loaded |

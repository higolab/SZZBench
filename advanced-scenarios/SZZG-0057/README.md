# SZZG-0057: Rebase old feature branch after unrelated main changes

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `old-base`, `unrelated-main-changes`, `direct-bic`, `origin-bic` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `m1`, `m2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `m1`, `m2` · BFC `c3` |
| graph features | 2 branches; rebase `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate rebase after unrelated main-line changes.

## Commit history

```text
c0: create initial correct implementation
f1: introduce bug on old feature base
m1: unrelated main change
m2: second unrelated main change
r1: rebase old feature BIC onto latest main
c3: fix bug after rebase onto latest main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce bug on old feature base |
| `m1` | `main` | c0 | `intermediate` | m1: unrelated main change |
| `m2` | `main` | m1 | `intermediate` | m2: second unrelated main change |
| `r1` | `main` | m2 | `bug_introducing` | r1: rebase old feature BIC onto latest main |
| `c3` | `main` | r1 | `bug_fixing` | c3: fix bug after rebase onto latest main |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, m1, m2
```

## Key property

m1/m2 are distractors; r1 is direct BIC.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Avoid m1/m2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

## Twin

[SZZG-0122](../SZZG-0122/README.md) is this scenario with the pre-rebase branch `feature` deleted after the rebase (`graph.ref_lifecycle.delete_branches`), so the origin `f1` is reachable from no ref. The oracle is identical; the pair separates tools that react to that difference from tools that do not.

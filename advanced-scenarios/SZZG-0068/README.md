# SZZG-0068: Rebase changes patch content during replay

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `patch-modified-during-rebase`, `origin-bic`, `direct-bic` |
| oracle | default: `exact_set`; required `r1`; related origins `f1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5) · BFC `c2` |
| graph features | 2 branches; rebase `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate direct/origin handling when rebase changes patch content.

## Commit history

```text
c0: create initial correct implementation
f1: introduce exclusive bug on feature
m1: add main note
r1: rebase feature bug with adjusted patch content
c2: fix adjusted lower-bound bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce exclusive bug on feature |
| `m1` | `main` | c0 | `intermediate` | m1: add main note |
| `r1` | `main` | m1 | `bug_introducing` | r1: rebase feature bug with adjusted patch content |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix adjusted lower-bound bug |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

Patch equality alone is insufficient.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Treat f1 as origin.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

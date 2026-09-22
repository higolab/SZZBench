# SZZG-0055: Release branch change rebased onto main

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `release-branch`, `release-to-main`, `direct-bic`, `origin-bic` |
| oracle | default: `exact_set`; required `r1`; related origins `rel1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `rel1` (credit 0.5) · BFC `c2` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate rebase from release branch to main.

## Commit history

```text
c0: create initial correct implementation
rel1: introduce release-specific range bug
m1: continue main development
r1: rebase release change onto main
c2: fix release-origin bug on main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `rel1` | `release` | c0 | `origin_bug_introducing` | rel1: introduce release-specific range bug |
| `m1` | `main` | c0 | `intermediate` | m1: continue main development |
| `r1` | `main` | m1 | `bug_introducing` | r1: rebase release change onto main |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix release-origin bug on main |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: rel1
```

## Key property

rel1 is origin, r1 is direct on main.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

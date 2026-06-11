# SZZG-0078: Multiple BICs replayed by rebase

## Purpose

Evaluate multiple-BIC handling when BICs are introduced by rebase replay.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce lower-bound bug
f2: f2: introduce upper-bound bug
r1: r1: rebase lower-bound BIC
r2: r2: rebase upper-bound BIC
c3: c3: fix both rebased BICs
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce lower-bound bug |
| `f2` | `feature` | f1 | `origin_bug_introducing` | f2: introduce upper-bound bug |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase lower-bound BIC |
| `r2` | `main` | r1 | `bug_introducing` | r2: rebase upper-bound BIC |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix both rebased BICs |

## Expected SZZ result

```text
Expected BIC(s): r1, r2
Related but not correct: f1, f2
```

## Key property

Origin BIC set maps to direct BIC set.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Return r1 and r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

# SZZG-0070: Rebase combines multiple BICs into one commit

## Purpose

Evaluate multiple-origin-to-one-direct BIC mapping after interactive rebase.

## Commit history

```text
c0: create initial correct implementation
f1: introduce lower-bound bug
f2: introduce upper-bound bug
r1: rebase combined boundary bugs as one commit
c2: fix combined rebased bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce lower-bound bug |
| `f2` | `feature` | f1 | `origin_bug_introducing` | f2: introduce upper-bound bug |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase combined boundary bugs as one commit |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix combined rebased bug |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, f2
```

## Key property

f1 and f2 become one direct commit r1.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

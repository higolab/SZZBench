# SZZG-0066: Rebase conflict resolution propagates existing bug

## Purpose

Evaluate direct-vs-origin BIC behavior when conflict resolution propagates an existing bug.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range bug on feature
m1: m1: add main-line documentation
r1: r1: resolve rebase conflict by taking buggy feature logic
c2: c2: fix propagated rebase bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range bug on feature |
| `m1` | `main` | c0 | `intermediate` | m1: add main-line documentation |
| `r1` | `main` | m1 | `bug_introducing` | r1: resolve rebase conflict by taking buggy feature logic |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix propagated rebase bug |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

The same buggy logic exists in f1, but main-line direct BIC is r1.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Treat f1 as origin.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

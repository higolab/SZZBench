# SZZG-0073: Interactive rebase reorders commits before BIC

## Purpose

Evaluate commit reordering during rebase.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: add feature docs
f2: f2: introduce range bug
r1: r1: replay docs before reordered BIC
r2: r2: replay bug commit after reorder
c3: c3: fix reordered bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `intermediate` | f1: add feature docs |
| `f2` | `feature` | f1 | `origin_bug_introducing` | f2: introduce range bug |
| `r1` | `main` | c0 | `intermediate` | r1: replay docs before reordered BIC |
| `r2` | `main` | r1 | `bug_introducing` | r2: replay bug commit after reorder |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix reordered bug |

## Expected SZZ result

```text
Expected BIC(s): r2
Related but not correct: f2, r1
```

## Key property

Only r2 introduces the bug after reorder.

## Difference from SZZG-0063

SZZG-0063 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r2.
- Avoid r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

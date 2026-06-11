# SZZG-0071: Interactive rebase edits BIC commit

## Purpose

Evaluate interactive rebase edit of a BIC.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce exclusive range bug
r1: r1: edit feature bug during interactive rebase
c2: c2: fix edited rebased bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce exclusive range bug |
| `r1` | `main` | c0 | `bug_introducing` | r1: edit feature bug during interactive rebase |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix edited rebased bug |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

r1 is an edited replay of f1.

## Difference from SZZG-0063

SZZG-0063 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

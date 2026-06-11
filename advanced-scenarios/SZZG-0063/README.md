# SZZG-0063: Rebase conflict resolution introduces bug

## Purpose

Evaluate a bug introduced by conflict resolution during rebase.

## Commit history

```text
c0: c0: create initial correct implementation
m1: m1: add main-line documentation
f1: f1: add feature documentation
r1: r1: resolve rebase conflict and introduce range bug
c2: c2: fix range bug from conflict resolution
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `m1` | `main` | c0 | `intermediate` | m1: add main-line documentation |
| `f1` | `feature` | c0 | `intermediate` | f1: add feature documentation |
| `r1` | `main` | m1 | `bug_introducing` | r1: resolve rebase conflict and introduce range bug |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix range bug from conflict resolution |

## Expected SZZ result

```text
Expected BIC(s): r1
```

## Key property

The feature commit is not the BIC; the conflict resolution commit is.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

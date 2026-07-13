# SZZG-0024: Clone diverges before rebase

## Purpose

Evaluate rebase combined with clone divergence.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: create buggy clone
f2: f2: diverge cloned buggy logic
r1: r1: rebase buggy clone creation
r2: r2: rebase clone divergence
c4: c4: fix diverged clone
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: create buggy clone |
| `f2` | `feature` | f1 | `origin_bug_introducing` | f2: diverge cloned buggy logic |
| `r1` | `main` | c0 | `intermediate` | r1: rebase buggy clone creation |
| `r2` | `main` | r1 | `bug_introducing` | r2: rebase clone divergence |
| `c4` | `main` | r2 | `bug_fixing` | c4: fix diverged clone |

## Expected SZZ result

```text
Expected BIC(s): r2
Related but not correct: r1, f1, f2
```

## Key property

The fixed instance is the diverged clone line introduced by r2.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

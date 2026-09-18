# SZZG-0024: Clone diverges before rebase

## Purpose

Evaluate rebase combined with clone divergence.

`r1` replays the faulty clone into `main`, the history the fix belongs to, so it is the direct BIC
(contract D4). `r2` replays the *annotation* — it appends `// cloned logic` to that line and changes no
behaviour at all, measured as 0 of 27648 probe answers moving across it — so it is never a BIC (D5), even
though it is the last commit to touch the line the fix deletes. `f1` is the feature-branch commit the clone
was replayed from, and is therefore the origin (D2).

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
Expected BIC(s): r1
Related origins: f1
Related but not correct: r2, f2
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

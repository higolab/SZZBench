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
c0: create initial correct implementation
f1: create buggy clone
f2: diverge cloned buggy logic
r1: rebase buggy clone creation
r2: rebase clone divergence
c4: fix diverged clone
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: create buggy clone |
| `f2` | `feature` | f1 | `origin_bug_introducing` | f2: diverge cloned buggy logic |
| `r1` | `main` | c0 | `bug_introducing` | r1: replays the faulty clone into main (direct BIC) |
| `r2` | `main` | r1 | `intermediate` | r2: replays the annotation; changes no behaviour |
| `c4` | `main` | r2 | `bug_fixing` | c4: fix diverged clone |

## Expected SZZ result

```text
Expected BIC(s): r1
Related origins: f1
Related but not correct: r2, f2
```

## Key property

The fixed instance is the cloned line that `r1` replayed into `main`. `r2`'s rebased annotation is the last
commit to touch that line, so a method that reports the last textual touch answers `r2` and is wrong.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report `r1`, not the annotation commit `r2` that last touched the line.
- Whether the replayed commit `r1` rather than its feature-branch source `f1` is reported.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

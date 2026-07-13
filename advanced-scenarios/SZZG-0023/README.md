# SZZG-0023: Rebase with copy propagation

## Purpose

Evaluate copy propagation through rebase.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range bug on feature
f2: f2: copy buggy range logic
r1: r1: rebase original bug
r2: r2: rebase copied buggy logic
c3: c3: fix copied range logic
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range bug on feature |
| `f2` | `feature` | f1 | `origin_bug_propagating` | f2: copy buggy range logic |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase original bug |
| `r2` | `main` | r1 | `bug_introducing` | r2: rebase copied buggy logic |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix copied range logic |

## Expected SZZ result

```text
Expected BIC(s): r2
Related but not correct: r1, f1, f2
```

## Key property

The fixed instance is in the copied file introduced by r2.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

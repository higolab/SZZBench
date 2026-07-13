# SZZG-0078: Rebase commit message reveals origin

## Purpose

Evaluate whether message context helps or misleads SZZ in a rebase scenario.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range boundary bug on feature
f2: f2: add feature helper using buggy range check
r1: r1: rebase f1 onto main and preserve origin reference
r2: r2: rebase feature helper onto main
c3: c3: fix range boundary bug after rebase
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range boundary bug on feature |
| `f2` | `feature` | f1 | `intermediate` | f2: add feature helper using buggy range check |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase f1 onto main and preserve origin reference |
| `r2` | `main` | r1 | `intermediate` | r2: rebase feature helper onto main |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix range boundary bug after rebase |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

The direct BIC remains r1 despite message context.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

# SZZG-0058: Bug-fixing commit is rebased onto main

## Purpose

Evaluate a BFC that is itself a rebased feature fix.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce bug on feature
f2: f2: fix bug on feature
r1: r1: rebase feature bug commit onto main
r2: r2: rebase feature fix commit onto main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce bug on feature |
| `f2` | `feature` | f1 | `origin_bug_fixing` | f2: fix bug on feature |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase feature bug commit onto main |
| `r2` | `main` | r1 | `bug_fixing` | r2: rebase feature fix commit onto main |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, f2
```

## Key property

r2 is the main-line BFC.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Start from r2.
- Return r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

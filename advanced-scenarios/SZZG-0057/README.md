# SZZG-0057: Rebase old feature branch after unrelated main changes

## Purpose

Evaluate rebase after unrelated main-line changes.

## Commit history

```text
c0: create initial correct implementation
f1: introduce bug on old feature base
m1: unrelated main change
m2: second unrelated main change
r1: rebase old feature BIC onto latest main
c3: fix bug after rebase onto latest main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce bug on old feature base |
| `m1` | `main` | c0 | `intermediate` | m1: unrelated main change |
| `m2` | `main` | m1 | `intermediate` | m2: second unrelated main change |
| `r1` | `main` | m2 | `bug_introducing` | r1: rebase old feature BIC onto latest main |
| `c3` | `main` | r1 | `bug_fixing` | c3: fix bug after rebase onto latest main |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, m1, m2
```

## Key property

m1/m2 are distractors; r1 is direct BIC.

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Avoid m1/m2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

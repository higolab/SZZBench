# SZZG-0079: Rebase splits original BIC into multiple commits

## Purpose

Evaluate one-origin-to-multiple-direct BIC mapping after rebase.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce both boundary bugs
r1: r1: rebase lower-bound part
r2: r2: rebase upper-bound part
c3: c3: fix both boundary bugs
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce both boundary bugs |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase lower-bound part |
| `r2` | `main` | r1 | `bug_introducing` | r2: rebase upper-bound part |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix both boundary bugs |

## Expected SZZ result

```text
Expected BIC(s): r1, r2
Related but not correct: f1
```

## Key property

f1 is split into r1 and r2.

## Difference from SZZG-0073

SZZG-0073 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Return r1 and r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

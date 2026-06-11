# SZZG-0070: Interactive rebase drops original BIC but bug remains

## Purpose

Evaluate dropped origin BIC with surviving buggy change.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce bug that will be dropped
f2: f2: add helper retaining buggy logic
r2: r2: replay helper after dropping original BIC
c3: c3: fix bug retained by helper
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce bug that will be dropped |
| `f2` | `feature` | f1 | `intermediate` | f2: add helper retaining buggy logic |
| `r2` | `main` | c0 | `bug_introducing` | r2: replay helper after dropping original BIC |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix bug retained by helper |

## Expected SZZ result

```text
Expected BIC(s): r2
Related but not correct: f1
```

## Key property

f1 is dropped; r2 is reachable direct BIC.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

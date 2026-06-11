# SZZG-0077: Interactive rebase squashes BIC and BFC into neutral commit

## Purpose

Clarify a scope boundary for bugs that do not survive into final main history.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce transient bug on feature
f2: f2: fix transient bug on feature
r1: r1: squash transient bug and fix into neutral commit
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `bug_introducing` | f1: introduce transient bug on feature |
| `f2` | `feature` | f1 | `bug_fixing` | f2: fix transient bug on feature |
| `r1` | `main` | c0 | `intermediate` | r1: squash transient bug and fix into neutral commit |

## Expected SZZ result

```text
Expected BIC(s): f1
```

## Key property

The final main history has no main-line BIC for this transient bug.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Record transient pair.
- Treat as special scope-boundary case.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

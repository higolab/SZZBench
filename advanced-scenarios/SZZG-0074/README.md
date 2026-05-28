# SZZG-0074: Rebase with non-BIC intermediate commit

## Purpose

Evaluate whether SZZ distinguishes a rebased BIC from a later rebased intermediate commit.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range boundary bug on feature
f2: f2: add feature helper using buggy range check
r1: r1: rebase feature BIC onto main
r2: r2: rebase feature helper onto main
c3: c3: fix range boundary bug after rebase
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range boundary bug on feature |
| `f2` | `feature` | f1 | `intermediate` | f2: add feature helper using buggy range check |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase feature BIC onto main |
| `r2` | `main` | r1 | `intermediate` | r2: rebase feature helper onto main |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix range boundary bug after rebase |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, r2
```

## Key property

r1 is the direct BIC; r2 is non-BIC intermediate.

## Difference from SZZG-0073

SZZG-0073 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Avoid r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

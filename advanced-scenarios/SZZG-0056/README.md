# SZZG-0056: Main fix rebased onto release branch

## Purpose

Evaluate a release BFC that is a rebased copy of a main fix.

## Commit history

```text
c0: c0: create initial correct implementation
c1: c1: introduce range bug on main
rel1: rel1: cut release branch with bug
c2: c2: fix bug on main
r2: r2: rebase main fix onto release
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `bug_introducing` | c1: introduce range bug on main |
| `rel1` | `release` | c1 | `release_branch_point` | rel1: cut release branch with bug |
| `c2` | `main` | c1 | `bug_fixing` | c2: fix bug on main |
| `r2` | `release` | rel1 | `bug_fixing` | r2: rebase main fix onto release |

## Expected SZZ result

```text
Expected BIC(s): c1
Related but not correct: c2
```

## Key property

r2 is the release BFC replaying c2.

## Difference from SZZG-0063

SZZG-0063 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Start from r2.
- Return c1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.

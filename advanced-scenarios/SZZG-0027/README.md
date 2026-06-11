# SZZG-0027: BIC before merge, BFC after merge

## Purpose

A bug is introduced on main before a feature branch is merged, and the bug is fixed on main after the merge.

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug on main before merge
c2: perform unrelated feature branch work
c3: merge feature branch into main
c4: fix the pre-merge bug on main after merge
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `bug_introducing` | c1: introduce range boundary bug on main before merge |
| `c2` | `feature` | c0 | `intermediate` | c2: add unrelated feature helper |
| `c3` | `main` | c1, c2 | `merge` | c3: merge feature branch after bug introduction |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix pre-merge range boundary bug |

## Expected SZZ result

```text
Expected BIC: c1
```

## Scenario purpose

Evaluate a BIC that exists before a merge and a BFC that appears after that merge.

## Notes

- This scenario separates pre-merge main-line bug introduction from feature-branch bug introduction.

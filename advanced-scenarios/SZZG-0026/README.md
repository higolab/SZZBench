# SZZG-0026: BIC on feature branch, BFC on main

## Purpose

A feature branch introduces a bug, extends feature code that depends on the buggy method, is merged into main, and is then fixed by a normal main-branch commit.

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug on feature branch
c2: extend feature branch code that uses the buggy method
c3: merge feature branch into main
c4: fix bug on main after merge
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `feature` | c0 | `bug_introducing` | c1: introduce range boundary bug on feature |
| `c2` | `feature` | c1 | `intermediate` | c2: extend feature branch code using range check |
| `c3` | `main` | c0, c2 | `merge` | c3: merge feature branch into main |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix range boundary bug on main |

## Expected SZZ result

```text
Expected BIC: c1
```

## Scenario purpose

Evaluate whether SZZ can identify a BIC located on a feature branch when the BFC is a normal commit on main after the feature branch has been merged.

## Notes

- This scenario is intentionally distinct from SZZG-0029 and SZZG-0005 because the BFC is not a merge commit.

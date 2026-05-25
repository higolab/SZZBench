# SZZG-0039: Criss-cross merge

## Overview

Two long-lived branches merge each other in both directions before a bug introduced on one branch is fixed.

## Commit history

```text
c0: create initial correct implementation
c1: branchA introduces bug
c2: branchB adds unrelated work
c3: branchA merges branchB
c4: branchB merges branchA
c5: branchB fixes the bug after criss-cross merges
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `branchA` | c0 | `bug_introducing` | c1: introduce range boundary bug on branchA |
| `c2` | `branchB` | c0 | `intermediate` | c2: add branchB reporter |
| `c3` | `branchA` | c1, c2 | `merge` | c3: merge branchB into branchA |
| `c4` | `branchB` | c2, c3 | `merge` | c4: merge branchA back into branchB |
| `c5` | `branchB` | c4 | `bug_fixing` | c5: fix range boundary bug after criss-cross merge |

## Expected SZZ result

```text
Expected BIC: c1
```

## Scenario purpose

Evaluate whether SZZ can identify a BIC when branch history includes reciprocal merges.

## Notes

- This scenario uses a simplified criss-cross-like DAG that current graph_generator should be able to create.

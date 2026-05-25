# SZZG-0033: BFC in merge commit

## Overview

A bug is introduced before branches diverge; main and feature apply complementary partial changes, and the merge commit performs the final fix.

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug before branch divergence
c2: main branch adds tests but does not fix the bug
c3: feature branch adds a helper that still uses the buggy method
c4: merge main and feature and fix the bug in the merge commit
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `bug_introducing` | c1: introduce shared range boundary bug |
| `c2` | `main` | c1 | `intermediate` | c2: add boundary test documentation without fixing code |
| `c3` | `feature` | c1 | `intermediate` | c3: add feature helper that depends on buggy range check |
| `c4` | `main` | c2, c3 | `bug_fixing` | c4: merge feature and complete range boundary fix |

## Expected SZZ result

```text
Expected BIC: c1
```

## Scenario purpose

Evaluate a BFC that is a merge commit, but with a different shape from SZZG-0005: the bug predates branch divergence and the merge completes the fix after partial contextual changes on both branches.

## Notes

- This is案B for distinguishing SZZG-0033 from SZZG-0005.

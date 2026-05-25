# SZZG-0040: Release-branch-only bug

## Overview

A release branch introduces and fixes a bug that never exists on main.

## Commit history

```text
c0: create initial correct implementation on main
c1: main continues correct development
c2: release branch introduces release-only bug
c3: main adds unrelated correct change
c4: release branch fixes release-only bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `intermediate` | c1: add main-only version note |
| `c2` | `release` | c0 | `bug_introducing` | c2: introduce release-only range boundary bug |
| `c3` | `main` | c1 | `intermediate` | c3: add unrelated main documentation |
| `c4` | `release` | c2 | `bug_fixing` | c4: fix release-only range boundary bug |

## Expected SZZ result

```text
Expected BIC: c2
```

## Scenario purpose

Evaluate whether SZZ can handle a bug that exists only on a release branch and not on main.

## Notes

- This scenario should not be collapsed into feature-to-main merge scenarios.

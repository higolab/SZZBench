# SZZG-0041: Fixed on main but unfixed on release

## Overview

A bug is introduced before a release branch is cut; main fixes the bug, but the release branch continues without the fix.

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug on main before release branch
c2: create release branch from buggy state and add release note
c3: fix bug on main
c4: release branch continues with bug unfixed
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `bug_introducing` | c1: introduce range boundary bug before release branch |
| `c2` | `release` | c1 | `intermediate` | c2: cut release branch from buggy state |
| `c3` | `main` | c1 | `bug_fixing` | c3: fix range boundary bug on main |
| `c4` | `release` | c2 | `unfixed_release` | c4: release branch continues without main fix |

## Expected SZZ result

```text
Expected BIC: c1
```

## Scenario purpose

Evaluate whether SZZ can identify the original BIC when a fix exists on main but has not been propagated to a release branch.

## Notes

- The release branch intentionally remains buggy at c4.

# SZZG-0033: Backport fix

## Purpose

This scenario represents a main-line fix that is backported to a release branch.

A bug is introduced on `main` before the release branch is cut. The release branch is created from the buggy state. Main fixes the bug and continues development. The release branch also receives release-specific changes. Finally, the main fix is backported to release.

## Commit graph

```text
main:     c0 ---- c1(BIC) ---- c2(BFC) ---- c3
                    \
release:             r0 ---- r1 ---- r2(BFC, backport of c2)
```

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug on main before release branch is cut
r0: create release branch from the buggy state and add release metadata
c2: fix bug on main
c3: continue main development after the fix
r1: add release-specific configuration while bug is still present on release
r2: backport main fix c2 onto release
```

## Oracle

Expected BIC:

```text
c1
```

Bug-fixing commits:

```text
c2: main-line fix
r2: release-branch backport fix
```

## Difference from SZZG-0024 and SZZG-0025

`SZZG-0024` and `SZZG-0025` are revert / reintroduction scenarios.

`SZZG-0033` is a branch and backport scenario. The release branch keeps the bug until the main-line fix is backported.

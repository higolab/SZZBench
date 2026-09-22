# SZZG-0059: Merge commit itself is the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `merge-commit`, `bug-introducing-merge`, `non-linear-history` |
| oracle | `exact_set`; required `c3` · BFC `c4` |
| defeats | `blame`, `shape` |
| graph features | 2 branches; merge commit `c3` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports a merge commit as the bug-introducing commit when the fault is in
the merge resolution.

## Expected history

```text
c0: create feature flag
c1: main branch hardens feature flag
c2: feature branch keeps simple flag
c3: merge feature branch and accidentally drop safety check
c4: fix dropped safety check
```

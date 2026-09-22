# SZZG-0060: BFC on main after feature-branch BIC is merged

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `feature-branch`, `merge-commit`, `bfc-after-merge` |
| oracle | `exact_set`; required `c1` · BFC `c4` |
| graph features | 2 branches; merge commit `c3` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reaches a feature-branch bug-introducing commit from a fix made on main
after the merge.

## Expected history

```text
c0: create quota checker
c1: feature branch introduces quota boundary bug
c2: main branch updates comments only
c3: merge feature branch
c4: fix quota boundary on main
```

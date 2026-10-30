# SZZG-0062: Backported fix on maintenance branch traces to original mainline BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `backport`, `maintenance-branch`, `cross-branch-bic` |
| oracle | `exact_set`; required `c1` · BFC `c4` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method traces a backported fix on a release branch to the main-line bug-
introducing commit.

## Expected history

```text
c0: create lock timeout
c1: introduce too-short timeout on main
c2: release branch cut from buggy main
c3: fix timeout on main
c4: backport timeout fix to release branch
```

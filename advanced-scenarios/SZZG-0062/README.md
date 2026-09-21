# SZZG-0062: Backported fix on maintenance branch traces to original mainline BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `backport`, `maintenance-branch`, `cross-branch-bic` |
| oracle | `exact_set`; required `c1` · BFC `c4` |
| graph features | 2 branches |
<!-- /szzbench:header -->

## Purpose

Evaluate backported fix on maintenance branch traces to original mainline bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create lock timeout
c1: introduce too-short timeout on main
c2: release branch cut from buggy main
c3: fix timeout on main
c4: backport timeout fix to release branch
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: backport, maintenance_branch, cross_branch_bic
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0062/
|-- scenario.graph.yml
`-- README.md
```

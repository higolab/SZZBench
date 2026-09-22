# SZZG-0060: BFC on main after feature-branch BIC is merged

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `feature-branch`, `merge-commit`, `bfc-after-merge` |
| oracle | `exact_set`; required `c1` · BFC `c4` |
| graph features | 2 branches; merge commit `c3` |
<!-- /szzbench:header -->

## Purpose

Evaluate bfc on main after feature-branch bic is merged and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create quota checker
c1: feature branch introduces quota boundary bug
c2: main branch updates comments only
c3: merge feature branch
c4: fix quota boundary on main
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: feature_branch, merge_commit, bfc_after_merge
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
SZZG-0060/
|-- scenario.graph.yml
`-- README.md
```

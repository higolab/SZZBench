# SZZG-0011: Bug introduced inside a refactoring commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `bug-introducing-refactoring`, `mixed-change`, `rename-method` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate bug introduced inside a refactoring commit and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create normalizer
c1: rename method and accidentally remove lower-case conversion
c2: fix normalization after refactoring
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: bug_introducing_refactoring, mixed_change, rename_method
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
SZZG-0011/
|-- scenario.graph.yml
`-- README.md
```

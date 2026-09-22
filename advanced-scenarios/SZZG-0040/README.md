# SZZG-0040: Multiple BICs where one true BIC is not directly touched by the BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bic`, `not-directly-touched-by-fix`, `context-dependent` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate multiple bics where one true bic is not directly touched by the bfc and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create retry policy
c1: introduce excessive retry limit
c2: introduce retry on client errors
c3: fix retry condition without touching retry limit
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: multiple_bic, not_directly_touched_by_fix, context_dependent
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1, c2
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0040/
|-- scenario.graph.yml
`-- README.md
```

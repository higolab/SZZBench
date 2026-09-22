# SZZG-0026: Copy followed by bug introduction only in the copied code

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `copy-propagation`, `clone-divergence`, `direct-bic-in-copy` |
| oracle | `exact_set`; required `c2` · BFC `c3` |
| graph features | operation `copy_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate copy followed by bug introduction only in the copied code and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create original formatter
c1: copy formatter to report formatter
c2: introduce copied-code null handling bug
c3: fix copied formatter null handling
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: copy_file, clone_divergence, direct_bic_in_copy
- Operation types: copy_file, replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c2
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0026/
|-- scenario.graph.yml
`-- README.md
```

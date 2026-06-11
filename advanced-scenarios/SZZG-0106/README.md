# SZZG-0106: Copy followed by bug introduction only in the copied code

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate copy followed by bug introduction only in the copied code and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create original formatter
c1: c1: copy formatter to report formatter
c2: c2: introduce copied-code null handling bug
c3: c3: fix copied formatter null handling
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0106/
|-- scenario.graph.yml
`-- README.md
```

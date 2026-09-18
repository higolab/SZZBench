# SZZG-0028: The copy and the later edit are both required; the origin is not

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate origin bic and direct copied-code bic are both required and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create amount parser
c1: c1: introduce original parser trim bug
c2: c2: copy amount parser to invoice parser
c3: c3: introduce copied parser sign bug
c4: c4: fix invoice parsing behavior
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, multiple_bic, origin_and_direct_bic
- Operation types: copy_file, replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1, c3
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
SZZG-0028/
|-- scenario.graph.yml
`-- README.md
```

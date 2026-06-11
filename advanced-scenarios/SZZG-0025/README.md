# SZZG-0025: Clone origin versus copied direct BIC

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate clone origin versus copied direct bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create original sanitizer
c1: c1: introduce bug in original sanitizer
c2: c2: copy sanitizer into admin module
c3: c3: fix copied sanitizer only
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, copy_file, origin_bic_policy
- Operation types: copy_file, replace, write_file
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0025/
|-- scenario.graph.yml
`-- README.md
```

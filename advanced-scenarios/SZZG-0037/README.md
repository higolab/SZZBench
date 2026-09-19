# SZZG-0037: One BFC fixes multiple BICs across multiple files

## Source

- Category: Multiple-BIC scenarios

## Purpose

Evaluate one bfc fixes multiple bics across multiple files and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial calculator and validator
c1: introduce rounding bug in calculator
c2: introduce zero-quantity validation bug
c3: fix both pricing and validation bugs
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: multiple_bic, multiple_file, single_bfc
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
SZZG-0037/
|-- scenario.graph.yml
`-- README.md
```

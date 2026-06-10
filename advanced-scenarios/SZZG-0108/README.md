# SZZG-0108: One directly blamed BIC and one context-only BIC

## Source

- Category: Multiple-BIC scenarios

## Purpose

Evaluate one directly blamed bic and one context-only bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create discount service
c1: c1: introduce wrong threshold
c2: c2: introduce wrong base discount
c3: c3: fix customer discount behavior by restoring threshold only
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: multiple_bic, context_dependent, partial_observability
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0108/
|-- scenario.graph.yml
`-- README.md
```

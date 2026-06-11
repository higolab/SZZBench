# SZZG-0039: Prerequisite BIC and symptom BIC fixed together

## Source

- Category: Multiple-BIC scenarios

## Purpose

Evaluate prerequisite bic and symptom bic fixed together and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create token verifier
c1: c1: weaken token trust predicate
c2: c2: weaken access control condition
c3: c3: fix access control vulnerability
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: multiple_bic, causal_chain, single_bfc
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
SZZG-0039/
|-- scenario.graph.yml
`-- README.md
```

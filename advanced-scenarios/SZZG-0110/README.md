# SZZG-0110: Configuration BIC is fixed by code-side normalization

## Source

- Category: Context-dependent scenarios

## Purpose

Evaluate configuration bic is fixed by code-side normalization and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create endpoint resolver and config
c1: c1: introduce trailing slash in configuration
c2: c2: fix endpoint construction in code
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: configuration_change, cross_artifact_fix, context_dependent
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0110/
|-- scenario.graph.yml
`-- README.md
```

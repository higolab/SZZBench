# SZZG-0011: Bug introduced inside a refactoring commit

## Source

- Category: Refactoring scenarios

## Purpose

Evaluate bug introduced inside a refactoring commit and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create normalizer
c1: c1: rename method and accidentally remove lower-case conversion
c2: c2: fix normalization after refactoring
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0011/
|-- scenario.graph.yml
`-- README.md
```

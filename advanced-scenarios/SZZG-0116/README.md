# SZZG-0116: Ambiguous blame with duplicate faulty lines

## Source

- Category: Ambiguous blame scenarios

## Purpose

Evaluate ambiguous blame with duplicate faulty lines and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create duplicate limit checks
c1: c1: introduce user limit bug
c2: c2: introduce syntactically identical admin limit bug
c3: c3: fix only user limit boundary
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: ambiguous_blame, duplicate_code, same_statement_multiple_locations
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
SZZG-0116/
|-- scenario.graph.yml
`-- README.md
```

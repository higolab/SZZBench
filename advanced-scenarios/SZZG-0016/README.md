# SZZG-0016: Partial credit when only some BICs are returned

## Source

- Category: Multiple BIC and BFC scenarios

## Purpose

Evaluate Partial credit when only some BICs are returned and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c1: create initial state (write_file src/main/java/example/Range.java)
c2: apply intermediate change (write_file docs/intermediate-note.md)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: expected_szz
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0016/
|-- scenario.graph.yml
`-- README.md
```

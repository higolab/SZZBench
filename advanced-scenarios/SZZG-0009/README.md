# SZZG-0009: File rename between BIC and BFC

## Source

- Source scenario: `FUTURE-009`
- Category: Intermediate-history scenarios

## Purpose

Evaluate File rename between BIC and BFC and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/OldRange.java)
c1: introduce bug (replace src/main/java/example/OldRange.java)
c2: apply intermediate change (rename_file src/main/java/example/OldRange.java -> src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: rename_file
- Operation types: write_file, replace, rename_file
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
SZZG-0009/
|-- scenario.graph.yml
`-- README.md
```

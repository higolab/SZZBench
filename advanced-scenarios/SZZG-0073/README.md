# SZZG-0073: Switching evaluated targets by benchmark variant

## Source

- Source scenario: `FUTURE-075`
- Category: Schema and evaluation-policy scenarios

## Purpose

Evaluate Switching evaluated targets by benchmark variant and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c1: introduce origin bug (write_file src/main/java/example/A.java)
c2: introduce bug (copy_file src/main/java/example/A.java -> src/main/java/example/B.java)
c3: fix bug (replace src/main/java/example/B.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: evaluation_variants, direct_bic, origin_bic, copy_propagation
- Operation types: write_file, copy_file, replace
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
SZZG-0073/
|-- scenario.graph.yml
`-- README.md
```

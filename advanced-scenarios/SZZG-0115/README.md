# SZZG-0115: Top-k evaluation

## Source

- Category: Schema and evaluation-policy scenarios

## Purpose

Evaluate Top-k evaluation and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/RangeService.java)
c1: introduce bug (replace src/main/java/example/RangeService.java)
c2: add distractor change (replace src/main/java/example/RangeService.java)
c3: add distractor change (write_file docs/range-service-notes.md)
c4: fix bug (replace src/main/java/example/RangeService.java)
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

## Files

```text
SZZG-0115/
|-- scenario.graph.yml
`-- README.md
```

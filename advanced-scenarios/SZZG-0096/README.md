# SZZG-0096: Multiple candidate BICs inside a work item

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate Multiple candidate BICs inside a work item and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/RangeService.java)
c1: add candidate change (replace src/main/java/example/RangeService.java)
c2: introduce bug (replace src/main/java/example/RangeService.java)
c3: add candidate change (replace src/main/java/example/RangeService.java)
c4: fix bug (replace src/main/java/example/RangeService.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: work_items, expected_szz
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
SZZG-0096/
|-- scenario.graph.yml
`-- README.md
```

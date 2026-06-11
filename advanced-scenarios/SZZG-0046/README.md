# SZZG-0046: Unrelated commits mixed in the same issue

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate Unrelated commits mixed in the same issue and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/RangeService.java)
c1: introduce bug (replace src/main/java/example/RangeService.java)
c2: add unrelated change (replace src/main/java/example/RangeService.java)
c3: add unrelated change (write_file docs/issue-10-note.md)
c4: fix bug (replace src/main/java/example/RangeService.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: work_items, issues
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
SZZG-0046/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0045: BIC separated from BFC by an intermediate work-item commit

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate whether SZZ identifies the original BIC when an unrelated intermediate work-item commit appears immediately before the BFC.

## Expected history

```text
c1: create initial state (write_file src/main/java/example/Range.java)
c2: apply unrelated work-item note (write_file docs/intermediate-note.md)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history uses graph-aware work-item metadata to mark the intermediate commit as a candidate in the same work-item series.

## Required graph-schema features

- Factors: work_items
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether an unrelated intermediate work-item commit is not mistaken for the BIC.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0045/
|-- scenario.graph.yml
`-- README.md
```

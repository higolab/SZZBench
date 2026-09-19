# SZZG-0095: BIC separated from BFC by an intermediate work-item commit

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate whether SZZ identifies the original BIC when a related but non-faulty work-item commit sits immediately between the BIC and BFC.

## Expected history

```text
c0: create inventory reservation logic
c1: introduce exact-stock reservation bug
c2: add unrelated audit event in the same work item
c3: fix exact-stock reservation bug
```

## Why this needs `scenario.graph.yml`

Work-item membership and related-but-not-correct candidates require metadata beyond the normal linear scenario schema.

## Required graph-schema features

- Factors: work_items, intermediate_commit, related_but_not_correct
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether the intermediate audit commit c2 is not mistaken for the BIC.
- Whether work-item membership is represented without collapsing all commits in the work item into one cause.

---

## Files

```text
SZZG-0095/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0094: BIC and BFC belong to the same issue commit series

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate whether issue-series context is preserved when the BIC and BFC both reference the same issue.

## Expected history

```text
c1: create initial range implementation
c2: ISSUE-101 implement boundary optimization but introduce bug
c3: ISSUE-101 fix inclusive boundary regression
```

## Why this needs `scenario.graph.yml`

Issue membership and linked commits require graph-aware contextual metadata.

## Required graph-schema features

- Factors: issues
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c2 as the BIC rather than the initial commit.
- Whether both the BIC and BFC are represented as part of ISSUE-101.
- Whether the expected_szz exact-set policy is applied correctly.

---

## Files

```text
SZZG-0094/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0007: BIC is a test-only commit

## Source

- Category: BIC property scenarios

## Purpose

Evaluate whether SZZ can report a BIC that only edits test code.

## Expected history

```text
c0: create correct Range code and boundary test
c1: introduce faulty boundary expectation in test only
c2: fix the test oracle
```

## Why this needs `scenario.graph.yml`

The bug is a faulty test oracle rather than a production source bug, so the expected BIC is a test-only commit.

## Required graph-schema features

- Factors: test_only_bic, expected_szz
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the test-only BIC.
- Whether production code remaining unchanged in the BIC is handled correctly.
- Whether the expected_szz exact-set policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0007/
|-- scenario.graph.yml
`-- README.md
```

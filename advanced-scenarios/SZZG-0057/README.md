# SZZG-0057: Cause can be inferred from test failure

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ can use failing-test context to connect the BFC to the parser-pattern BIC.

## Expected history

```text
c0: create ISO event date parser
c1: introduce locale-specific parser pattern
c2: add failing webhook date regression test
c3: restore ISO parser pattern
```

## Why this needs `scenario.graph.yml`

The key clue is in the failing test message and the regression test added after the BIC.

## Required graph-schema features

- Factors: test_context, context
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether the failing test message points to ISO date parsing rather than generic parser churn.
- Whether the test commit c2 is not mistaken for a BIC.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0057/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0064: Empty intermediate commit

## Source

- Category: Robustness and implementation-quality scenarios

## Purpose

Evaluate whether SZZ identifies the real BIC when an empty commit appears in the intermediate history.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: apply empty intermediate change
c2: introduce bug (replace src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: allow_empty
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether the empty intermediate commit c1 is not reported as the BIC.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0064/
|-- scenario.graph.yml
`-- README.md
```

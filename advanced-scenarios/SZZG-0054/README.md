# SZZG-0054: Chmod-only intermediate

## Source

- Category: Robustness and implementation-quality scenarios

## Purpose

Evaluate whether SZZ identifies the real BIC when a chmod-only commit appears in the intermediate history.

## Expected history

```text
c0: create initial state (write_file scripts/run.sh; write_file src/main/java/example/Range.java)
c1: apply intermediate change (chmod scripts/run.sh)
c2: introduce bug (replace src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: chmod
- Operation types: write_file, chmod, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether the chmod-only intermediate commit c1 is not reported as the BIC.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0054/
|-- scenario.graph.yml
`-- README.md
```

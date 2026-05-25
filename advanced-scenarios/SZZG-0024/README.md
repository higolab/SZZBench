# SZZG-0024: Same bug introduced independently

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate Same bug introduced independently and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/IndependentRanges.java)
c1: introduce bug (replace src/main/java/example/IndependentRanges.java)
c2: introduce bug (replace src/main/java/example/IndependentRanges.java)
c3: fix bug (replace src/main/java/example/IndependentRanges.java; replace src/main/java/example/IndependentRanges.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

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
SZZG-0024/
|-- scenario.graph.yml
`-- README.md
```

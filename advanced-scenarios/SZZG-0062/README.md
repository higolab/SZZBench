# SZZG-0062: File deletion

## Source

- Category: Robustness and implementation-quality scenarios

## Purpose

Evaluate File deletion and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Buggy.java)
c1: fix bug (delete_file src/main/java/example/Buggy.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: delete_file
- Operation types: write_file, delete_file
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
SZZG-0062/
|-- scenario.graph.yml
`-- README.md
```

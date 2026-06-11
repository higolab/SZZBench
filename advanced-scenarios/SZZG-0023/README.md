# SZZG-0023: Clone removal as fix

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate Clone removal as fix and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/A.java)
c1: introduce bug (write_file src/main/java/example/B.java)
c2: fix bug (delete_file src/main/java/example/B.java; write_file docs/clone-removal.md)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: clone_relationships
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
SZZG-0023/
|-- scenario.graph.yml
`-- README.md
```

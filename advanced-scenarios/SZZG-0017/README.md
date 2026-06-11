# SZZG-0017: Clone diverges before fix

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate Clone diverges before fix and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: introduce origin bug (write_file src/main/java/example/A.java)
c1: introduce bug (copy_file src/main/java/example/A.java -> src/main/java/example/B.java)
c2: diverge clone (replace src/main/java/example/B.java; replace src/main/java/example/B.java)
c3: fix bug (replace src/main/java/example/B.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: clone_relationships
- Operation types: write_file, copy_file, replace
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
SZZG-0017/
|-- scenario.graph.yml
`-- README.md
```

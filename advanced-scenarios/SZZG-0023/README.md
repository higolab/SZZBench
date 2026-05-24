# SZZG-0023: Only one clone instance is fixed first

## Source

- Source scenario: `FUTURE-023`
- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate Only one clone instance is fixed first and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: introduce origin bug (write_file src/main/java/example/A.java)
c1: introduce bug (copy_file src/main/java/example/A.java -> src/main/java/example/B.java)
c2: fix bug (replace src/main/java/example/A.java)
c3: fix bug (replace src/main/java/example/B.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: clone_relationships, bug_instances
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
SZZG-0023/
|-- scenario.graph.yml
`-- README.md
```

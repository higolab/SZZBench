# SZZG-0053: Line moved and duplicated

## Source

- Category: Ambiguous blame and duplicate-code scenarios

## Purpose

Evaluate Line moved and duplicated and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c1: create initial state (write_file src/main/java/example/Range.java)
c2: apply intermediate change (move_entity; copy_entity)
c3: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: move_entity, copy_entity, bug_instances
- Operation types: write_file, move_entity, copy_entity, replace
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
SZZG-0053/
|-- scenario.graph.yml
`-- README.md
```

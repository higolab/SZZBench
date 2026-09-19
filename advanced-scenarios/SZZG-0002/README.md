# SZZG-0002: BFC performs file move and fix in the same commit

## Source

- Category: BFC shape scenarios

## Purpose

Evaluate BFC performs file move and fix in the same commit and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: fix bug (move_file src/main/java/example/Range.java -> src/main/java/domain/Range.java; replace src/main/java/domain/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: move_file
- Operation types: write_file, replace, move_file
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0002/
|-- scenario.graph.yml
`-- README.md
```

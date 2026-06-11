# SZZG-0007: Line moved and duplicated

## Source

- Category: Ambiguous blame and duplicate-code scenarios

## Purpose

Evaluate a bug whose faulty line is introduced in `Range.java`, then moved and duplicated into `RangeUtils.java` before the fix.

The required BIC remains `c1`. Commit `c2` is propagation history only: it moves and duplicates an already buggy line and should not replace the original BIC.

## Expected history

```text
c1: create initial buggy range implementation (write_file src/main/java/example/Range.java)
c2: move and duplicate the existing buggy range check (move_entity; copy_entity)
c3: fix moved duplicated bug (replace src/main/java/example/RangeUtils.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: move_entity, copy_entity, bug_instances
- Operation types: write_file, move_entity, copy_entity, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `c1` as the original BIC despite the move and duplicate in `c2`.
- Whether SZZ does not treat the move/copy commit `c2` as the direct BIC.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0007/
|-- scenario.graph.yml
`-- README.md
```

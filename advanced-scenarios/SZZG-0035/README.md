# SZZG-0035: Cherry-pick BIC

## Source

- Category: Branch, merge, cherry-pick, and backport scenarios

## Purpose

Evaluate Cherry-pick BIC and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: apply intermediate change (write_file docs/feature-note.md)
c3: merge branch
c4: fix bug (replace src/main/java/example/Range.java)
r1: cherry-pick change (apply_patch_from c1)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: branch, cherry_pick_of
- Operation types: write_file, replace, apply_patch_from
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
SZZG-0035/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0004: File move between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `file-rename`, `file-move` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `move_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate File move between BIC and BFC and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: apply intermediate change (move_file src/main/java/example/Range.java -> src/main/java/domain/Range.java)
c3: fix bug (replace src/main/java/domain/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: rename_file, move_file
- Operation types: write_file, replace, move_file
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0004/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0036: Fix split across multiple commits

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bfc` |
| oracle | `exact_set`; required `c1` · BFCs `c3`, `c4` |
| graph features | 2 BFCs; `fix_series` |
<!-- /szzbench:header -->

## Purpose

Evaluate Fix split across multiple commits and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: add test context (write_file src/test/java/example/RangeTest.java)
c3: fix bug (replace src/main/java/example/Range.java)
c4: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: bug_fixing_commits
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0036/
|-- scenario.graph.yml
`-- README.md
```

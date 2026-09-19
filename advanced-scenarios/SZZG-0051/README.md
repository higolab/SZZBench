# SZZG-0051: Backport introduces release-specific bug

## Source

- Category: Branch, merge, cherry-pick, and backport scenarios

## Purpose

Evaluate a release-specific regression introduced while adapting a main-line source change onto a release branch.

Commit `c1` is not a BFC. It is the main-line source change that adds `RangePolicy.java`. Commit `r1` is a release-side backport/adaptation of that source change, and it introduces the boundary bug in `Range.java`. The expected BIC is therefore `r1`, not `c1`.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: add main range policy source change (write_file src/main/java/example/RangePolicy.java)
r1: backport range policy to release and introduce boundary bug (replace src/main/java/example/Range.java; write_file src/main/java/example/RangePolicy.java)
r2: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: branch, backport_of
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `r1` as the release-specific BIC.
- Whether `backport_of: c1` metadata does not cause SZZ to blame the main-line source change `c1`.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0051/
|-- scenario.graph.yml
`-- README.md
```

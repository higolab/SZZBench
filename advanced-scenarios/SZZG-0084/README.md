# SZZG-0084: Partial revert reintroduces bug

## Source

- Category: Revert and reintroduction scenarios

## Purpose

Evaluate a partial revert where `c3` reintroduces the boundary bug and is the expected direct BIC for the final fix.

The original BIC `c1` is related history, but the `reintroduction_direct` oracle requires the reintroducing commit `c3`.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: fix bug (replace src/main/java/example/Range.java)
c3: partially revert c2 and reintroduce bug (replace src/main/java/example/Range.java)
c4: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `c3` as the reintroducing BIC for the final fix.
- Whether SZZ treats the original BIC `c1` as related history, not the required direct answer.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0084/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0115: Cherry-picked BIC appears as duplicate commits on two branches

## Source

- Category: Branch and merge scenarios

## Purpose

Evaluate cherry-picked bic appears as duplicate commits on two branches and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create status mapper
c1: c1: introduce wrong error status on release branch
c2: c2: cherry-pick wrong error status onto main
c3: c3: fix wrong error status on main
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: cherry_pick, duplicate_patch, non_linear_history
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c2
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0115/
|-- scenario.graph.yml
`-- README.md
```

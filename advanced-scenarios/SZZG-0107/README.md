# SZZG-0107: Clone divergence before fixing one clone

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate clone divergence before fixing one clone and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create base permission check
c1: c1: introduce permissive delete check
c2: c2: clone policy to group policy
c3: c3: diverge copied clone by renaming parameters
c4: c4: fix copied clone after divergence
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, clone_divergence, ambiguous_blame
- Operation types: copy_file, replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1
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
SZZG-0107/
|-- scenario.graph.yml
`-- README.md
```

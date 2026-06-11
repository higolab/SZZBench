# SZZG-0113: Merge commit itself is the BIC

## Source

- Category: Branch and merge scenarios

## Purpose

Evaluate merge commit itself is the bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create feature flag
c1: c1: main branch hardens feature flag
c2: c2: feature branch keeps simple flag
c3: c3: merge feature branch and accidentally drop safety check
c4: c4: fix dropped safety check
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: merge_commit, bug_introducing_merge, non_linear_history
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c3
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
SZZG-0113/
|-- scenario.graph.yml
`-- README.md
```

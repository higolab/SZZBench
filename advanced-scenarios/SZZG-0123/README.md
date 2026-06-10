# SZZG-0123: Defensive check BFC masks an earlier root-cause BIC

## Source

- Category: Context-dependent scenarios

## Purpose

Evaluate defensive check bfc masks an earlier root-cause bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create profile renderer
c1: c1: introduce null-producing root cause
c2: c2: fix crash with defensive null checks
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: defensive_fix, root_cause_not_touched, context_dependent
- Operation types: replace, write_file
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
SZZG-0123/
|-- scenario.graph.yml
`-- README.md
```

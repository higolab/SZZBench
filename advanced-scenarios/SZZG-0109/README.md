# SZZG-0109: Caller-side context is needed to identify the BIC

## Source

- Category: Context-dependent scenarios

## Purpose

Evaluate caller-side context is needed to identify the bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create account service and caller
c1: c1: introduce caller-side inversion bug
c2: c2: fix login behavior by changing callee condition
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: context_dependent, caller_callee, not_directly_local
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
SZZG-0109/
|-- scenario.graph.yml
`-- README.md
```

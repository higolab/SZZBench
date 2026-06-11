# SZZG-0022: Explicit evaluation of direct BIC vs origin BIC

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate direct-BIC versus origin-BIC accounting for copied buggy code.

## Expected history

```text
c0: create correct original range implementation
c1: introduce bug in original Range
c2: copy buggy Range into CopiedRange
c3: fix CopiedRange only
```

## Why this needs `scenario.graph.yml`

Direct and origin BIC roles require graph-aware bug metadata and evaluation policy.

## Required graph-schema features

- Factors: copy_file, expected_szz, direct_bic, origin_bic
- Operation types: write_file, replace, copy_file
- Expected SZZ policy distinguishes direct-only and origin-aware variants.

## Evaluation points

- Whether SZZ identifies c2 as the direct BIC for `CopiedRange`.
- Whether c1 is tracked as the origin BIC without being required under direct-only scoring.
- Whether evaluation variants can distinguish direct-only and origin-aware policies.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0022/
|-- scenario.graph.yml
`-- README.md
```

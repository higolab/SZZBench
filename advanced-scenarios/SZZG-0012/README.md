# SZZG-0012: BFC performs method extraction and bug fix in the same commit

## Source

- Category: Refactoring scenarios

## Purpose

Evaluate bfc performs method extraction and bug fix in the same commit and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create tax calculator
c1: introduce tax rounding bug
c2: extract tax rate helper and fix rounding
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: bfc_refactoring, extract_method, mixed_bfc
- Operation types: insert_after, replace, write_file
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

## Files

```text
SZZG-0012/
|-- scenario.graph.yml
`-- README.md
```

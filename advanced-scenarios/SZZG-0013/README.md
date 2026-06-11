# SZZG-0013: Semantic-preserving rewrite between BIC and BFC

## Source

- Category: Intermediate-history scenarios

## Purpose

Evaluate semantic-preserving rewrite between bic and bfc and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create age gate
c1: c1: introduce boundary bug
c2: c2: rewrite condition into explicit if statement
c3: c3: fix adult boundary after rewrite
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: intermediate_rewrite, formatting, line_history_break
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
SZZG-0013/
|-- scenario.graph.yml
`-- README.md
```

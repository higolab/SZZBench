# SZZG-0009: Intermediate method extraction between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `intermediate-refactoring`, `extract-method`, `line-history-break` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `insert_after` |
<!-- /szzbench:header -->

## Purpose

Evaluate intermediate method extraction between bic and bfc and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create shipping fee calculation
c1: introduce free-shipping threshold bug
c2: extract free-shipping predicate
c3: fix extracted threshold predicate
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: intermediate_refactoring, extract_method, line_history_break
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
SZZG-0009/
|-- scenario.graph.yml
`-- README.md
```

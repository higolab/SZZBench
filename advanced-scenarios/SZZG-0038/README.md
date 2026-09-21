# SZZG-0038: One directly blamed BIC and one context-only BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bic`, `context-dependent`, `partial-observability` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate one directly blamed bic and one context-only bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create discount service
c1: introduce wrong threshold
c2: introduce wrong base discount
c3: fix customer discount behavior by restoring threshold only
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: multiple_bic, context_dependent, partial_observability
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1, c2
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0038/
|-- scenario.graph.yml
`-- README.md
```

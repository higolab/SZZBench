# SZZG-0010: Intermediate file move and package rename between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `file-rename`, `file-move`, `package-rename`, `intermediate-refactoring` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `rename_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate intermediate file move and package rename between bic and bfc and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create legacy parser
c1: introduce parser trimming bug
c2: move parser to core package
c3: fix parser whitespace handling
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: rename_file, move_file, package_rename, intermediate_refactoring
- Operation types: rename_file, replace, write_file
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
SZZG-0010/
|-- scenario.graph.yml
`-- README.md
```

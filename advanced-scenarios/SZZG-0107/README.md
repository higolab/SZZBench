# SZZG-0107: BFC includes generated files

## Source

- Category: BFC shape scenarios

## Purpose

Evaluate whether SZZ identifies the source BIC when the BFC contains both the real source fix and generated-file noise.

## Expected history

```text
c0: create correct range implementation
c1: introduce exclusive-boundary bug
c2: fix range bug and update generated boundary table
```

## Why this needs `scenario.graph.yml`

The BFC combines a normal source-code fix with a generated artifact update, which is represented explicitly with graph operations.

## Required graph-schema features

- Factors: generated_files
- Operation types: write_file, replace, write_generated_text_file
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether generated files added or refreshed in the BFC are ignored as blame targets.
- Whether the expected_szz exact-set policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0107/
|-- scenario.graph.yml
`-- README.md
```

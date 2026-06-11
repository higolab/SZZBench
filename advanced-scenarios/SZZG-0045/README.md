# SZZG-0045: BFC message references the wrong commit

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate whether SZZ resists an incorrect BFC-message hint and still identifies the true code-level BIC.

## Expected history

```text
c0: create currency rounding helper
c1: introduce truncating cents normalization
c2: add invoice label helper mentioned by mistake
c3: fix rounding while incorrectly blaming c2 in the message
```

## Why this needs `scenario.graph.yml`

The BFC contains a misleading developer hint that must be represented separately from the code-level fault metadata.

## Required graph-schema features

- Factors: developer_hints, misleading_commit_message
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the true rounding BIC.
- Whether c2 is treated as an incorrect message reference rather than the expected BIC.
- Whether developer hints are distinguished from trustworthy blame evidence.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0045/
|-- scenario.graph.yml
`-- README.md
```

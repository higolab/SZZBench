# SZZG-0112: Non-UTF-8 file

## Source

- Category: Robustness and implementation-quality scenarios

## Purpose

Evaluate whether SZZBench tooling handles non-UTF-8 files without assuming all changed files are UTF-8 text.

## Expected history

```text
c0: create CP1252-encoded boundary configuration
c1: introduce boundary bug in the non-UTF-8 config
c2: fix the non-UTF-8 config
```

## Why this needs `scenario.graph.yml`

The non-UTF-8 file is modeled with `write_binary_file` so that invalid UTF-8 bytes can be represented safely.

## Required graph-schema features

- Factors: encoding, non_utf8_file, write_binary_file
- Operation types: write_file, write_binary_file
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC for the encoded configuration change.
- Whether non-UTF-8 file content does not break parsing, generation, or verification.
- Whether the expected_szz exact-set policy is applied correctly.

---

## Files

```text
SZZG-0112/
|-- scenario.graph.yml
`-- README.md
```

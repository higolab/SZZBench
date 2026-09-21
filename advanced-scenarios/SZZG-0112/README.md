# SZZG-0112: Non-UTF-8 file

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `encoding`, `non-utf8-file`, `binary-file` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `write_binary_file` |
<!-- /szzbench:header -->

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

## Evaluation points

- Whether SZZ identifies c1 as the BIC for the encoded configuration change.
- Whether non-UTF-8 file content does not break parsing, generation, or verification.
- Whether the expected_szz exact-set policy is applied correctly.

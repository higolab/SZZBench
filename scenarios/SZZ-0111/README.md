# SZZ-0111: Generated-looking repetitive code

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `robustness`, `generated-code`, `duplicate-statement` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario is intended to stress implementation robustness under noisy or repetitive code conditions.

## Commit structure

- `c0`: Initial generated-looking implementation
- `c1`: Introduce bug in repetitive code
- `c2`: Fix repetitive-code bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

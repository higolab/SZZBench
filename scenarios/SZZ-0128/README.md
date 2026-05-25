# SZZ-0128: Validation weakening plus caller acceptance

## Purpose

This scenario requires treating two bug-introducing commits as contributing to the same later fix.

## Commit structure

- `c0`: initial implementation
- `c1`: weakens the validator
- `c2`: makes the caller accept an additional invalid value
- `c3`: fixes both contributing changes

## Expected behavior

The expected BFC is `c3`; the expected BIC set is `{c1, c2}`.

## Factors

- `multi-bic`
- `single-bfc`
- `line-modification`

# SZZ-0093: If-else to guard clause after BIC

## Purpose

This scenario inserts an intermediate refactoring change between the BIC and BFC.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Apply intermediate rewrite
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `guard-clause-after-bic`

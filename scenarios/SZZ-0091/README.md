# SZZ-0091: Inline helper after BIC

## Purpose

This scenario inserts an intermediate refactoring change between the BIC and BFC.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Inline helper after bug introduction
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `inline-method-after-bic`

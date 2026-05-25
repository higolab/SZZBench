# SZZ-0092: Loop to conditional rewrite after BIC

## Purpose

This scenario inserts an intermediate refactoring change between the BIC and BFC.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Rewrite loop to conditional after bug introduction
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `loop-rewrite-after-bic`

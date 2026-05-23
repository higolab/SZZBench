# SZZ-0052: BFC with test file addition

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC with test file addition.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Fix bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `bfc-test-addition`

# SZZ-0123: BFC with two faulty expressions fixed

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC with two faulty expressions fixed.

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
- `multiple-line-bfc`

# SZZ-0060: BFC restores division guard condition

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit restores a boolean guard condition for a division denominator check.

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
- `comparison-error`

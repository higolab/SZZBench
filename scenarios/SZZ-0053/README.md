# SZZ-0053: BFC with comment update

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC with comment update.

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
- `bfc-comment-change`

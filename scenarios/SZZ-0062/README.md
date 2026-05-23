# SZZ-0062: BFC changes default branch in conditional

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC changes default branch in conditional.

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
- `conditional-default`

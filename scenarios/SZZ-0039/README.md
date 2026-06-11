# SZZ-0039: Wrong parameter used in new feature

## Purpose

This scenario evaluates a bug-introducing commit shape: Wrong parameter used in new feature.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `feature-addition-bic`
- `wrong-variable`

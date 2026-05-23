# SZZ-0123: Off-by-one in new loop boundary

## Purpose

This scenario evaluates a bug-introducing commit shape: Off-by-one in new loop boundary.

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
- `off-by-one`

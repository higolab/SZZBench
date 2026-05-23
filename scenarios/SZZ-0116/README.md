# SZZ-0116: Configuration-like constant change introduces bug

## Purpose

This scenario evaluates a bug-introducing commit shape: Configuration-like constant change introduces bug.

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
- `configuration-bic`

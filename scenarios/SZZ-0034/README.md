# SZZ-0034: API call change introduces bug

## Purpose

This scenario evaluates a bug-introducing commit shape: API call change introduces bug.

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
- `api-misuse-bic`

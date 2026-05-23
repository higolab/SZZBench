# SZZ-0110: Formatting and bug introduced together

## Purpose

This scenario evaluates a bug-introducing commit shape: Formatting and bug introduced together.

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
- `formatting-and-bug-bic`

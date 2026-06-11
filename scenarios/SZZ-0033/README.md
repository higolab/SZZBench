# SZZ-0033: Refactoring introduces comparison bug

## Purpose

This scenario evaluates a bug-introducing commit shape: Refactoring introduces comparison bug.

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
- `refactoring-bic`

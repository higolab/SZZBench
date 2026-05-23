# SZZ-0038: Incorrect string normalization

## Purpose

This scenario introduces a bug by changing `return value.trim().toLowerCase();` to `return value.toLowerCase();` and later restores the correct implementation.

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
- `api-misuse`

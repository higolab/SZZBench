# SZZ-0012: Logical conjunction error

## Purpose

This scenario introduces a bug by changing `return hasName && hasEmail;` to `return hasName || hasEmail;` and later restores the correct implementation.

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
- `logical-operator-error`

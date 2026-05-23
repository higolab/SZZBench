# SZZ-0039: Wrong substring end

## Purpose

This scenario introduces a bug by changing `return value.substring(0, Math.min(3, value.length()));` to `return value.substring(0, 3);` and later restores the correct implementation.

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

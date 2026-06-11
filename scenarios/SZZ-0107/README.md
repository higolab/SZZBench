# SZZ-0107: Large commit with small bug

## Purpose

This scenario evaluates a bug-introducing commit shape: Large commit with small bug.

## Commit structure

- `c0`: initial correct implementation
- `c1`: large cleanup commit that introduces a small bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `large-bic`
- `tangled-bic`

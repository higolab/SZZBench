# SZZ-0154: Root cause described in BIC message

## Purpose

This scenario is intended for evaluating SZZ variants that use commit messages or broader patch context.

## Commit structure

- `c0`: initial implementation
- `c1`: introduces the bug with a message that describes the root cause
- `c2`: BFC with message: Fix normalization regression

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `context-aware`

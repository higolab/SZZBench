# SZZ-0157: BFC message explicitly references BIC

## Purpose

This scenario is intended for evaluating SZZ variants that use commit messages or broader patch context.

## Commit structure

- `c0`: initial implementation
- `c1`: introduces the bug
- `c2`: BFC with message: Fix bug introduced by c1

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `context-aware`

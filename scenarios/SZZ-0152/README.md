# SZZ-0152: Issue-like message in BFC

## Purpose

This scenario is intended for evaluating SZZ variants that use commit messages or broader patch context.

## Commit structure

- `c0`: initial implementation
- `c1`: introduces the bug
- `c2`: BFC with message: ISSUE-1 fix missing inclusive boundary

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `context-aware`

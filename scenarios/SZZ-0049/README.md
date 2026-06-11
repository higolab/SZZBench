# SZZ-0049: Security validation omission

## Purpose

This scenario checks a security-related omission bug where a path validation
method lacks a guard against path traversal.

## Commit structure

- `c0`: Introduces an empty path policy class.
- `c1`: Adds a permissive `isSafe` method. This is the BIC.
- `c2`: Adds the missing path traversal guard. This is the BFC.

## Expected behavior

The expected BIC is `c1`, but line-level deleted-line SZZ is not directly
applicable because the fix adds a missing security guard.

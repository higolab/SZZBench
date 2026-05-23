# SZZ-0001: Simple line modification

## Purpose

This scenario checks whether a basic line-based SZZ implementation can identify
a single bug-introducing commit from a simple line modification.

## Commit structure

- `c0`: Introduces the correct implementation.
- `c1`: Introduces the bug by changing inclusive boundary checks to strict checks.
- `c2`: Fixes the bug by restoring the inclusive boundary checks.

## Expected behavior

The bug-fixing commit is `c2`.
The expected bug-introducing commit is `c1`.

This scenario is intended as a sanity check.

# SZZ-0002: Boolean return value modification

## Purpose

This scenario checks a simple single-line semantic bug where a predicate method
is changed to always return `true`.

## Commit structure

- `c0`: Introduces the correct predicate.
- `c1`: Replaces the predicate with `return true;`. This is the BIC.
- `c2`: Restores the original predicate. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for bug `B001`.

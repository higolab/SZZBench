# SZZ-0010: Tangled bug-introducing commit

## Purpose

This scenario checks a tangled BIC: the bug-introducing commit contains both a
faulty change and an unrelated helper-method addition.

## Commit structure

- `c0`: Correct range implementation.
- `c1`: Introduces the bug and adds an unrelated helper method. This is the BIC.
- `c2`: Fixes the boundary condition. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for `B001`.

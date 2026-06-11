# SZZ-0115: Tangled bug-fixing commit

## Purpose

This scenario checks a tangled BFC: the fixing commit contains both the real fix
and an unrelated helper-method addition.

## Commit structure

- `c0`: Correct implementation.
- `c1`: Introduces the strict boundary bug. This is the BIC.
- `c2`: Fixes the bug and adds an unrelated helper method. This is the BFC.

## Expected behavior

SZZ should use the actual fix hunk and report `c1` as the bug-introducing commit.

# SZZ-0004: Conditional expression change

## Purpose

This scenario checks a common conditional-expression bug: an inclusive comparison
is changed to a strict comparison.

## Commit structure

- `c0`: Allows payments when `amount <= balance`.
- `c1`: Changes the condition to `amount < balance`. This is the BIC.
- `c2`: Restores `amount <= balance`. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for bug `B001`.

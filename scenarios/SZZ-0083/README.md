# SZZ-0083: Whitespace-only rewrite after bug introduction

## Purpose

This scenario checks whether SZZ implementations incorrectly identify a
whitespace-only rewrite as the BIC.

## Commit structure

- `c0`: Correct inclusive range check.
- `c1`: Introduces the strict range bug. This is the expected BIC.
- `c2`: Changes whitespace in the faulty line only. This is a distractor.
- `c3`: Fixes the condition. This is the BFC.

## Expected behavior

SZZ should report `c1`, not the whitespace-only commit `c2`.

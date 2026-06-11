# SZZ-0081: Formatting after bug introduction

## Purpose

This scenario checks whether SZZ implementations are robust against a
formatting-only commit inserted between the BIC and the BFC.

## Commit structure

- `c0`: Introduces the correct implementation.
- `c1`: Introduces the boundary-check bug. This is the expected BIC.
- `c2`: Reformats the file and rewrites the faulty line. This is a distractor.
- `c3`: Fixes the bug. This is the BFC.

## Expected behavior

The bug-fixing commit is `c3`.
The expected bug-introducing commit is `c1`.

A simple line-based blame may incorrectly point to `c2`, because `c2` rewrites
the faulty line during formatting.

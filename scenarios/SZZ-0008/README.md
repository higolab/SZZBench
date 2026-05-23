# SZZ-0008: Formatting-only rewrite after bug introduction

## Purpose

This scenario checks whether SZZ implementations confuse a formatting-only
rewrite with the original bug-introducing commit.

## Commit structure

- `c0`: Introduces the correct inclusive condition.
- `c1`: Introduces the strict boundary bug. This is the expected BIC.
- `c2`: Reformats the faulty expression into multiple lines. This is a distractor.
- `c3`: Fixes the formatted expression. This is the BFC.

## Expected behavior

SZZ should report `c1`, not the formatting commit `c2`.

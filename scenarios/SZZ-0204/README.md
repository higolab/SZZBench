# SZZ-0204: Type annotation added to the faulty line after the BIC

## Purpose

The Python form of "the faulty line was rewritten without a behaviour
change before the fix". Here the rewrite is a type-hinting pass: it annotates
the parameters, the return type and the two local assignments, one of which
carries the fault. Java scenarios in this range add annotations or change
generic types on *other* lines (SZZ-0094, SZZ-0095); this one lands the noise
on the faulty line itself, so plain blame at the fix's parent stops at the
annotation commit. `git blame -w` does not help: `: bool` is not whitespace.

## Commit structure

- `c0`: `src/cache/expiry.py` with `is_expired(age_days, ttl_days)`. The
  docstring fixes the contract — an entry is still valid on the last day of
  its TTL — and the code computes `expired = remaining < 0`.
- `c1`: "Expire cache entries on the last day of their TTL": `remaining < 0`
  becomes `remaining <= 0`, contradicting the docstring. This is the **BIC**.
- `c2`: "Add type hints to the expiry helper": the header becomes
  `def is_expired(age_days: int, ttl_days: int) -> bool:`, and the two
  assignments become `remaining: int = ...` and
  `expired: bool = remaining <= 0`. Behaviour is unchanged. This is the
  planted distractor.
- `c3`: `expired: bool = remaining < 0`. This is the **BFC**.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor and the rewrite of the faulty line is declared by the factor
`type-annotation-rewrite`, so the validator's W320/W430 and the verifier's
"statement not present" finding are reported as information (I701).

## Behaviour at each commit

`[is_expired(a, 10) for a in (9, 10, 11)]`:

| commit | result |
|---|---|
| `c0` | `[False, False, True]` |
| `c1` | `[False, True, True]` |
| `c2` | `[False, True, True]` |
| `c3` | `[False, False, True]` |

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes one line, line 11,
`    expired: bool = remaining <= 0`.

- `git blame` at `c3^` attributes it to `c2`.
- `git blame -w` at `c3^` attributes it to `c2` as well.

Blame class of plain blame: **miss** — B-SZZ returns `{c2}`.

## What a tool must do

Look through a rewrite that keeps the expression and adds an annotation:
follow the line's history one more step (`git log -L`, or blame again at
`c2^`), or recognise `c2` as behaviour-preserving (an AST comparison with
annotations stripped finds `c1..c2` empty). A tool that reports `{c2}` has
blamed a type-hinting commit for a boundary fault.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `boundary-condition`
- `deep-line-history`
- `basic-blame-distractor`
- `type-annotation-rewrite`

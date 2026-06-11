# SZZ-0137: Null handling and empty handling changed separately

## Purpose

This scenario requires treating two bug-introducing commits as contributing to the same later fix.

## Commit structure

- `c0`: initial implementation
- `c1`: first contributing BIC
- `c2`: second contributing BIC
- `c3`: BFC

## Expected behavior

The expected BFC is `c3`; the expected BIC set is `{c1, c2}`.

## Factors

- `multi-bic`
- `single-bfc`
- `line-modification`

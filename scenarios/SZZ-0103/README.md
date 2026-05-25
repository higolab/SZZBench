# SZZ-0103: Comment deletion after BIC

## Purpose

This scenario inserts an intermediate intermediate-history change between the BIC and BFC.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Delete comment after bug introduction
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `comment-deletion-after-bic`

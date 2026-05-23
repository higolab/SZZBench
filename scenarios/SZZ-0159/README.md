# SZZ-0159: Comment-only intermediate before fix

## Purpose

This scenario is intended to stress implementation robustness under noisy or repetitive code conditions.

## Commit structure

- `c0`: Initial implementation
- `c1`: Introduce bug
- `c2`: Add comment-only context
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `comment-only-intermediate`

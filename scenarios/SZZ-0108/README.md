# SZZ-0108: CRLF-like full file rewrite

## Purpose

This scenario is intended to stress implementation robustness under noisy or repetitive code conditions.

## Commit structure

- `c0`: Initial implementation
- `c1`: Introduce bug
- `c2`: Fix bug after line-ending-like rewrite

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `line-ending-noise`

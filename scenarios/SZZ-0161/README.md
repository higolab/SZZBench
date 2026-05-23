# SZZ-0161: Generated-looking repetitive code

## Purpose

This scenario is intended to stress implementation robustness under noisy or repetitive code conditions.

## Commit structure

- `c0`: Initial generated-looking implementation
- `c1`: Introduce bug in repetitive code
- `c2`: Fix repetitive-code bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `generated-code`
- `duplicate-statement`

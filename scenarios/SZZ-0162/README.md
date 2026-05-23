# SZZ-0162: Huge method surrounding small bug

## Purpose

This scenario is intended to stress implementation robustness under noisy or repetitive code conditions.

## Commit structure

- `c0`: Initial large method
- `c1`: Introduce small bug in large method
- `c2`: Fix small bug in large method

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `large-method`
- `small-fault`

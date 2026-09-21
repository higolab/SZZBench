# SZZG-0056: Main fix rebased onto release branch

## Purpose

`Bytes.toBits` multiplies in `long`; `c1` drops the `L` and the `int` product
wraps for inputs above 256 MiB before it is widened to the `long` return type.
A release branch is cut from the buggy state; `main` fixes the line; the fix is
replayed onto `release` by rebase (`r2`, `rebase_of: c2`). Two BFCs, one BIC,
and a rebased fix whose source commit `c2` is `related_but_not_correct` — a
fix, not a cause.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 3, one distractor on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 6eafce9  2024-07-02  Multiply in long on release: toBits overflows past 256 MiB  <- BFC (r2, release; rebase_of c2)
* 3cb6328  2024-06-24  Cut the 1.0 release branch                                  (rel1, release; release/version.txt)
| * 96ea9f9  2024-06-27  Multiply in long: toBits overflows past 256 MiB           <- BFC (c2, main)
|/
* e6743a0  2024-06-18  Drop the long arithmetic in toBits                          <- BIC (c1)
* a7a1011  2024-06-10  Add the byte-to-bit conversion                              (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`, `related_but_not_correct: [c2]`)
- BFCs: `c2` on `main`, `r2` on `release`

## Measured behaviour and blame

| commit | `toBits(1 << 28)` | `toBits(1024)` |
|---|---|---|
| `c0` | 2147483648 | 8192 |
| `c1`, `rel1` | **-2147483648** | 8192 |
| `c2`, `r2` | 2147483648 | 8192 |

Small inputs are unaffected, so the fault needs an input above 256 MiB to show.
Both fixes delete the same line (`return bytes * 8;`, line 6); blame at `c2^`
and at `r2^` returns `c1` (verifier `GI703`).

## What a tool must do

Starting from `r2`, report `c1` — not `c2`, the commit `r2` replays, which is a
fix and is listed as `related_but_not_correct`.

## Factors

- `branch`
- `rebase`
- `release-branch`
- `main-fix-to-release`
- `rebased-bfc`
- `multi-bfc`
- `integer-overflow`

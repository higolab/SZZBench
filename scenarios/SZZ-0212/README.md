# SZZ-0212: A whitespace-only reformat between two faults takes ownership of the first

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `formatting-noise`, `boundary-condition`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S3 (issue #35): the answer is two
commits, and one of them sits one whitespace-only hop behind the commit blame
names. S3's controls already show that plain blame stops at a reformat
([SZZ-0083](../SZZ-0083/README.md) is that case with a single BIC, which the
second-commit rule solves). Here the reformat sits *between* two independent
faults that one commit fixes, so a tool that takes blame's answer gets one
commit right, misses one and adds one that changed no token — and every
positional rule fails, because the oracle has two commits.

## Commit structure

```text
c0  Add the shipping fee calculation           weightGrams <= FREE_UP_TO_GRAMS; base + surcharge
c1  Tighten the free-shipping weight check     weightGrams < FREE_UP_TO_GRAMS                  <- BIC
c2  Re-indent ShippingFee to the two-space style   every line rewritten, no token changed (noise)
c3  Rework how the surcharge enters the total  base - surcharge                                <- BIC
c4  Ship parcels at the free limit for free and add the express surcharge   both lines restored   <- BFC
```

`c2` rewrites every line of the file — four-space indentation becomes two-space
— and changes nothing else; `git diff -w c1 c2` is empty.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

## Measured behaviour

`feeCents(weightGrams, express)` for 1999, 2000 and 2001 grams, standard (S)
and express (X) delivery, at each commit (`tests/test_rebalance_scenarios.py`):

| commit | 1999 S | 1999 X | 2000 S | 2000 X | 2001 S | 2001 X |
|---|---|---|---|---|---|---|
| `c0` | 0 | 500 | 0 | 500 | 300 | 800 |
| `c1` | 0 | 500 | **300** | **800** | 300 | 800 |
| `c2` | 0 | 500 | 300 | 800 | 300 | 800 |
| `c3` | 0 | **-500** | 300 | **-200** | 300 | **-200** |
| `c4` | 0 | 500 | 0 | 500 | 300 | 800 |

`c1` moves the two 2000-gram answers, `c3` the three express answers, and the
2000-gram express parcel is wrong for both reasons at `c3`; `c2` moves nothing.
The fix restores exactly the four answers that are wrong at `c3`, the union of
the two effects. The two faults are independent, so the evidence for both
being necessary is the partial fix, measured at `c3`: restoring only the weight
check leaves the express answers at -500, -500 and -200; restoring only the
surcharge leaves the 2000-gram answers at 300 and 800.

## Measured blame outcome at BFC^

The fix deletes two lines:

```text
"int base = weightGrams < FREE_UP_TO_GRAMS ? 0 : STANDARD_FEE_CENTS;"   plain -> c2   -w -> c1   -w -C -C -> c1
"return base - surcharge;"                                             plain -> c3   -w -> c3   -w -C -C -> c3
```

Plain blame returns `{c2, c3}`: it misses `c1` and adds `c2`, the
re-indentation. `-w` reaches `c1`, because `c2` changed only the leading
whitespace of that line.

## What a tool must do to pass

Report exactly `{c1, c3}`. The commit blame names for the weight check, `c2`,
changed no token; the fault it carries was written one whitespace-only hop
earlier. `git blame -w`, or a walk that steps past any commit whose diff is
empty under `-w`, reaches `c1`; a tool that stops at blame's answer reports
`c2` and not `c1`.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

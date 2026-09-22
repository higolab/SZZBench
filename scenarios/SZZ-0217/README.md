# SZZ-0217: The fix message quotes the commit that changed what the callee returns

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `message-evidence`, `caller-callee`, `value-flow`, `wrong-constant`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S7 (issue #35). S7's controls put the
evidence a tool needs in the commit message or in code the diff does not show
([SZZ-0159](../SZZ-0159/README.md), [SZZ-0169](../SZZ-0169/README.md)), with a
single BIC that the second-commit rule finds anyway. Here the history is the
*callee* kind of the measured axis — a callee changes what it returns and its
only caller is converted with it, then a new caller assumes the old contract,
as in [SZZ-0191](../SZZ-0191/README.md) — and S7's evidence sits on top: the fix
message says why it divides and quotes the subject of the commit that changed
the callee. Blame reaches the new caller only; the message, or the callee the
fixed line calls, is the route to the other half.

## Commit structure

```text
c0  Add the duration text parser and the request timeout   parse("90s") = 90 (seconds); RequestTimeout.seconds() = parse()
c1  Return durations in milliseconds from DurationText.parse   parse() * 1000; RequestTimeout divides by 1000   <- BIC
c2  Document the accepted duration suffixes                 docs only (distractor)
c3  Add the retry delay setting                             RetryDelay.seconds() = parse()                      <- BIC
c4  Divide the parsed retry delay by 1000: DurationText.parse has returned milliseconds since "Return durations in milliseconds from DurationText.parse"   <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. Without `c3` nothing reads the parser's result as seconds;
without `c1` the parser returns seconds and `c3`'s caller is right.

## Measured behaviour

`RequestTimeout.seconds("90s")`, `RequestTimeout.seconds("2m")`,
`RetryDelay.seconds("90s")` and `RetryDelay.seconds("2m")` at each commit
(`tests/test_rebalance_scenarios.py`; `RetryDelay` exists from `c3`):

| commit | timeout "90s" | timeout "2m" | retry "90s" | retry "2m" |
|---|---|---|---|---|
| `c0`–`c2` | 90 | 120 | — | — |
| `c3` | 90 | 120 | **90000** | **120000** |
| `c4` | 90 | 120 | 90 | 120 |

`c1` changes no answer: the parser and its only caller change together.
**Counterfactual, measured:** undoing `c1` on top of `c3` — the parser back to
seconds, `RequestTimeout` no longer dividing — gives 90 and 120 for the retry
delay, the fixed answers.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return DurationText.parse(configured);"    plain -> c3    -w -> c3    -w -C -C -> c3
```

Blame returns `{c3}`. `c1` is not reachable from the deleted line: `c3` created
`RetryDelay.java`, and `c1` touched two other files.

## The evidence a tool can use

- The fix message quotes `c1`'s subject verbatim; `git log --grep` on that
  subject returns `c1` and `c4`, and `c1` is the one that is not the fix.
- The fixed expression calls `DurationText.parse`; the commit that last changed
  what it returns is `c1`, whose Javadoc line changed from seconds to
  milliseconds.

## What a tool must do to pass

Report exactly `{c1, c3}`. Either route reaches `c1`: following the callee from
the fixed expression, or reading the fix message and finding the commit it
quotes. A tool that reports `{c3}` alone has answered where the fault became
visible, not what caused it.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

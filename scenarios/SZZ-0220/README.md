# SZZ-0220: The fix also deletes the deprecated alias an intermediate commit added, so blame names one commit too many

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `tangled-bfc`, `multi-hunk-bfc`, `blame-over-reports`, `boundary-condition`, `wrong-operator` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The suite's second `discriminating` scenario whose failure is a **false
positive**, after [SZZ-0218](../SZZ-0218/README.md), and the first in S3, where
all thirty-nine other members have a one-commit oracle that a positional rule
names by construction. Two faults are repaired by one commit that also drops a
deprecated alias no caller uses, so blaming what it deletes returns both
required commits and two more.

## Commit structure

```text
c0  Add the password policy                     longEnough: length >= 8; score: length * 2
c1  Require more than the minimum length        length > 8                                  <- BIC
c2  Add a deprecated alias for the old method name   isLongEnough forwards to longEnough    (distractor)
c3  Rework the strength score                   length / 2                                  <- BIC
c4  Accept a password of exactly the minimum length, score by length again, and drop the unused alias   <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

`c2` is not a BIC. Its alias forwards to `longEnough` and nothing calls it, so
adding or removing it changes no answer.

## Measured behaviour

`longEnough` on passwords of 7, 8 and 9 characters, and `score` on an
eight-character password, at each commit (`tests/test_largest_pockets.py`):

| commit | 7 chars | 8 chars | 9 chars | score(8 chars) |
|---|---|---|---|---|
| `c0` | F | T | T | 16 |
| `c1` | F | **F** | T | 16 |
| `c2` | F | F | T | 16 |
| `c3` | F | F | T | **4** |
| `c4` | F | T | T | 16 |

`c2` moves nothing. Both faults are independent, and the partial fix at `c3`
shows both are needed: restoring the comparison alone leaves the score at 4,
restoring the score alone still rejects an eight-character password.

## Measured blame outcome at BFC^

The fix deletes eight lines across three hunks:

```text
"return value.length() > 8;"                        -> c1
"}"                                                 -> c0
""                                                  -> c0
"/** @deprecated renamed to longEnough */"          -> c2
"@Deprecated"                                       -> c2
"public boolean isLongEnough(String value) {"       -> c2
"return longEnough(value);"                         -> c2
"return value.length() / 2;"                        -> c3
```

Blame returns **`{c0, c1, c2, c3}`** — a strict superset of the answer. The
alias's own lines blame to `c2`; the closing brace and blank line above them
blame to `c0`, because the block removed begins with a `}` and a blank line and
git's aligner takes the first such pair in the file. No blame variant changes
this: every one of those lines really was written where blame says.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching both answers is what plain blame already
does; the work is rejecting the other two. Neither carries behaviour: the alias
is dead code that forwards to the method it aliases, and the brace and blank
line are punctuation the aligner attributed. A tool that treats every deleted
line as evidence reports four commits, and one that filters only on syntax
still has to decide that a dead forwarding method is not a cause.

## Difficulty

`hard`, above the `medium` floor its `extra` blame class sets
(`decisions/vocabulary.md` §4). The floor grades how far a tool must travel to
reach the answer, and here it travels nowhere: the whole difficulty is in
rejecting what blame hands over with the right commits.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

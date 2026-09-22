# SZZ-0214: A null check deleted while nothing reached it, a caller added later, and a fix that only adds

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `addition-only-fix`, `null-check-omission`, `prerequisite-bic`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S2 (issue #35). S2's controls show
that blame has nothing to work from when a fix only adds lines
([SZZ-0174](../SZZ-0174/README.md)), or when the BIC only deletes and the BFC
only adds ([SZZ-0177](../SZZ-0177/README.md)) — single-BIC cases that the
second-commit rule still solves. Here the deleted check was *unreachable* when
it was deleted, so the deletion changes nothing observable; the fault appears
when a later commit passes a nullable value; and the fix, the check put back,
deletes no line. The answer is two commits, blame has no deleted line to start
from, and the two sit at positions 1 and 3 of the history.

## Commit structure

```text
c0  Add the name normaliser and the greeting     normalize() returns "" for null; greet() passes a required login name
c1  Drop the null check from normalize(): its caller passes a required name   deletes three lines, adds none   <- BIC
c2  Add the farewell line                        Greeting.java only (distractor)
c3  Show the chosen nickname on the profile      Profile.displayName(nickname) passes a nullable nickname   <- BIC
c4  Treat a missing name as empty in normalize() the check put back: adds three lines, deletes none   <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. Without `c3` nothing passes `null` and the missing check is
never reached; without `c1` `normalize(null)` returns `""` and `c3`'s profile
shows an empty name, which is the fixed behaviour.

## Measured behaviour

`greet(" Ada ")`, `farewell(" Ada ")`, `displayName(" Ada ")` and
`displayName(null)` at each commit (`tests/test_rebalance_scenarios.py`;
`farewell` exists from `c2`, `Profile` from `c3`):

| commit | greet | farewell | displayName(" Ada ") | displayName(null) |
|---|---|---|---|---|
| `c0` | Hello, ada! | — | — | — |
| `c1` | Hello, ada! | — | — | — |
| `c2` | Hello, ada! | Goodbye, ada. | — | — |
| `c3` | Hello, ada! | Goodbye, ada. | ada | **NullPointerException** |
| `c4` | Hello, ada! | Goodbye, ada. | ada | `""` |

`c1` changes no answer of any entry point that exists at `c1`: `greet` is the
only caller of `normalize` and passes a required name. The counterfactual of
the other interaction scenarios — undoing the unreachable commit on top of the
later one — coincides with the fix here: putting the check back on top of `c3`
*is* `c4`, and it gives `""` for `displayName(null)`.

## Measured blame outcome at BFC^

The fix deletes no line: `git diff -U0 c4^ c4` consists of three `+` lines, so
there is nothing to blame. The scenario declares `addition-only-fix`, which
`W420` checks against the generated history. `c1` deletes three lines and adds
none (measured; it is not declared `deletion-only-bic`, because that
declaration is checked against every BIC of the bug and `c3` creates a file).

## What a tool must do to pass

Report exactly `{c1, c3}`. With no deleted line, a tool has to start from what
the fix *adds*: the check guards `raw`, so the commits to find are the one that
removed the same check — `c1`, whose deleted lines are the lines the fix adds —
and the one that first passed a nullable value into the method — `c3`, in a
file the fix never opens.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

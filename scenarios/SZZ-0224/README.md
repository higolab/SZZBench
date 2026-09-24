# SZZ-0224: The contract that changed is in a Javadoc, and the caller written afterwards follows the old one

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `root-cause-not-in-diff`, `caller-callee`, `value-flow`, `off-by-one`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S7's second `discriminating` scenario, after
[SZZ-0217](../SZZ-0217/README.md). S7 is the category where the evidence a tool
needs is not in the diff; SZZ-0217 puts it in the **commit message**, which
`git log --grep` can find. Here it is a **sentence in a Javadoc** — part of the
source, versioned like any line, and reachable only by reading the callee the
fixed line calls and then asking who changed what that sentence says.

## Commit structure

```text
c0  Add the retry limit and the import runner   attempts() = 3 (package-private), "the first attempt included"; the import loops i < attempts()
c1  Count retries after the first attempt rather than attempts in total   attempts() = 2, the Javadoc rewritten, the import loops i <= attempts()   <- BIC
c2  Note where the import runner is used        a class Javadoc (distractor)
c3  Retry the export the same way as the import  a new runner that loops i < attempts()   <- BIC
c4  Give the export the same number of runs as the import   i <= attempts()               <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. Without `c3` nothing reads `attempts()` under the old
contract; without `c1` the value is 3 and `c3`'s loop is right.

## Measured behaviour

`runsFor` on the import runner and on the export runner, over −1, 0, 1, 2, 3, 5
and `Integer.MAX_VALUE`, at each commit (`tests/test_deepened_categories.py`;
the export runner exists from `c3`):

| commit | `ImportRunner.runsFor` | `ExportRunner.runsFor` |
|---|---|---|
| `c0` | 1, 1, 2, 3, 3, 3, 3 | — |
| `c1`, `c2` | 1, 1, 2, 3, 3, 3, 3 | — |
| `c3` | 1, 1, 2, 3, 3, 3, 3 | 1, 1, 2, **2**, **2**, **2**, **2** |
| `c4` | 1, 1, 2, 3, 3, 3, 3 | 1, 1, 2, 3, 3, 3, 3 |

Those two methods are the package's **entire public surface**: `RetryLimit` is
package-private and so is `attempts()`, so no caller outside `example` can read
the number `c1` changes. `c1` therefore moves nothing observable — it halves
what `attempts()` means and adjusts the one loop that reads it in the same
commit, so the import still runs three times for every input.

(An earlier revision of this scenario left `RetryLimit` and `attempts()`
public. Then `attempts()` itself answered 3 at `c0` and 2 at `c1`, and the
latent-change premise was false for an external caller — found in the review of
PR #86 and fixed by narrowing the helper to the package that uses it.)

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"for (int i = 0; i < limit.attempts(); i++) {"    plain -> c3    -w -> c3    -w -C -C -> c3
```

Blame returns `{c3}`. `c1` is in `RetryLimit.java` and `ImportRunner.java`,
neither of which the fix opens.

## The evidence a tool can use

The Javadoc above the package-private `attempts()` reads *"How many times an operation may be
retried, not counting the first attempt"*. At `c0` the same sentence read *"in
total, the first attempt included"*. A tool that reads the callee the fixed line
calls, and blames the sentence rather than the code, lands on `c1` — the commit
that changed both the number and its meaning.

## What a tool must do to pass

Report exactly `{c1, c3}`. `c3` is blame's answer. Reaching `c1` means treating
the callee's documented contract as part of the fault's history: the loop is
short because the thing it counts stopped counting the first attempt, and the
sentence that says so is versioned.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

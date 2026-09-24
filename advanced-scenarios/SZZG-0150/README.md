# SZZG-0150: The merge resolves the conflict by inlining, and owns the boundary the branch moved

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `merge`, `semantic-preserving-rewrite`, `refactoring-after-bic`, `value-flow`, `off-by-one`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c4` · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
| graph features | 2 branches; merge commit `c3`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

G1's second `discriminating` scenario, after
[SZZG-0119](../SZZG-0119/README.md). Both are the *rewrite* kind — a
behaviour-preserving change owns the line an earlier fault is on — but
SZZG-0119's rewrite is an ordinary commit, and this one's is a **merge's
conflict resolution**. Main renamed the constant while a branch moved the
boundary, so the resolution writes lines that match neither parent, and blame
attributes the whole semantic change to the merge.

## Commit structure

```text
c0  main         Add the heavy-parcel surcharge    HEAVY_KILOGRAMS = 20; heavy() is >= over a named local
c1  band-rules   State the heavy band as a strict comparison   HEAVY_KILOGRAMS = 19; heavy() is >   <- BIC
c2  main         Name the heavy band after the weight it starts at   rename to HEAVY_FROM_KILOGRAMS, + Javadoc
c3  main         Merge the band rules, keeping one expression   resolution: the new name, the branch's value, one expression
c4  main         Show the weight the surcharge starts at   heavyFrom() = HEAVY_FROM_KILOGRAMS + " kg and over"   <- BIC
c5  main         Name the first weight that pays the surcharge   (HEAVY_FROM_KILOGRAMS + 1) + " kg and over"      <- BFC
```

`c1` is on the `band-rules` branch, which forks at `c0` and is merged at `c3`.
The merge conflicts: both parents rewrote the same two lines. The resolution
keeps main's name and the branch's comparison —
`static final int HEAVY_FROM_KILOGRAMS = 19;` and
`return kilograms > HEAVY_FROM_KILOGRAMS;` — and neither line exists in either
parent.

## Expected BIC / BFC

- BICs: `c1` and `c4` (`exact_set`, `required: [c1, c4]`)
- BFC: `c5`

Both are necessary. Without `c4` nothing reads the constant as a weight;
without `c1` the constant is 20 and `c4`'s label is right.

## Measured behaviour (from the generated repository)

`Bands.heavy` and `Quote.surchargeCents` over `Integer.MIN_VALUE`, 0, 18, 19,
20, 21 and `Integer.MAX_VALUE` — which, with `heavyFrom`, is the package's whole
public surface, because the constant is package-private
(`tests/test_graph_deepened_categories.py`):

| commit | `heavy` | `surchargeCents` | `heavyFrom` |
|---|---|---|---|
| `c0` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | — |
| `c2` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | — |
| `c1` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | — |
| `c3` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | — |
| `c4` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | **"19 kg and over"** |
| `c5` | F F F F T T T | 0, 0, 0, 0, 500, 500, 500 | "20 kg and over" |

`k >= 20` and `k > 19` are the same predicate over the integers, so `c1` moves
nothing an outside caller can see, and neither does the merge. The surcharge
starts at 20 kg throughout; only the sentence that names that weight is wrong,
from `c4` until `c5`.

## Measured blame outcome at BFC^

The fix deletes one line, and the two lines a value-flow step leads to are
blamed as well:

```text
Quote.java  "return Bands.HEAVY_FROM_KILOGRAMS + \" kg and over\";"  plain -> c4  -w -> c4  -w -C -C -> c4
Bands.java  "return kilograms > HEAVY_FROM_KILOGRAMS;"               plain -> c3  -w -> c3  -w -C -C -> c3
Bands.java  "static final int HEAVY_FROM_KILOGRAMS = 19;"            plain -> c3  -w -> c3  -w -C -C -> c3
```

Blame returns `{c4}`. Following the constant one step further reaches the
**merge**, not the commit that lowered it: `git log --first-parent` gives
`c5, c4, c3, c2, c0`, and `c1` appears only when the merge's second parent is
walked.

## What a tool must do to pass

Report exactly `{c1, c4}`. `c4` is blame's answer. Reaching `c1` means treating
a merge resolution as a commit that *carries* a change rather than makes one:
the boundary the resolution wrote came from the branch, and the branch commit
that moved it is off the first-parent history.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

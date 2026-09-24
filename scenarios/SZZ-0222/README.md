# SZZ-0222: Blame answers one commit and every one of them is wrong: an omission restored beside a duplicate guard removed

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `addition-only-fix`, `tangled-bfc`, `prerequisite-bic`, `null-check-omission`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S2's second `discriminating` scenario, after
[SZZ-0214](../SZZ-0214/README.md), and the suite's first where blame's answer
contains **no** required commit at all. SZZ-0214 leaves blame with nothing to
say: its fix deletes no line. Here the fix does delete a line — a null check a
merge had left duplicated — so blame answers confidently, and its answer is
entirely wrong.

## Commit structure

```text
c0  Add the upload validator                    null check, per-item size check
c1  Let the storage layer decide what is too large   the size check is deleted        <- BIC
c2  Keep both null checks after the merge       the null check appears twice (distractor)
c3  Accept a whole batch of uploads at once, item by item   no batch-total check      <- BIC
c4  Refuse an oversized upload again and drop the duplicated null check               <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Two independent omissions: `c1` deleted the per-item check, `c3` wrote a batch
entry point without a total check. The fix adds both back.

## Measured behaviour

`accept("a.txt", 1000)`, `accept("a.txt", 2000000)`, and `acceptBatch` with an
oversized item and with three items under the item limit but over the batch
limit, at each commit (`tests/test_deepened_categories.py`; `acceptBatch` exists
from `c3`):

| commit | small | oversized | batch with an oversized item | batch over the total | 2048 items of 1 MiB |
|---|---|---|---|---|---|
| `c0` | T | F | — | — | — |
| `c1`, `c2` | T | **T** | — | — | — |
| `c3` | T | **T** | **true** | **true** | **true** |
| `c4` | T | F | false | false | false |

The last probe is the batch whose sizes sum past the `int` range: 2048 files of
one mebibyte each pass `accept` individually and total two gibibytes. The fix
accumulates in 64 bits, so it refuses them; an `int` total would wrap negative
and accept the batch (`tests/test_reference_arithmetic.py` holds that bound).

## Measured blame outcome at BFC^

Both repairs add lines. The only line the fix deletes belongs to the duplicated
null check, and git's aligner takes the first of the pair:

```text
"if (name == null) {"    plain -> c0    -w -> c0    -w -C -C -> c0
```

Blame returns **`{c0}`** — the initial commit, which introduced nothing. No true
positive, one false positive. Every blame variant agrees, because `c0` really
did write that line.

## What a tool must do to pass

Report exactly `{c1, c3}`. The single answer blame offers has to be discarded
outright, which is harder than discarding an extra alongside two right ones:
there is nothing correct in the answer to anchor on. Both required commits have
to be reached from what the fix *adds* — a size check, back to the commit that
deleted it, and a batch-total check, back to the commit that wrote the batch
path without one.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

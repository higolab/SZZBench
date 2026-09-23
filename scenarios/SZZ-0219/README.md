# SZZ-0219: Two faults with two behaviour-preserving rewrites of the first one's line between them

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `deep-line-history`, `rewrite-depth-2`, `refactoring-after-bic`, `candidate-selection-distractor`, `boundary-condition`, `off-by-one`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c4` · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S3's controls put one behaviour-preserving rewrite between a single BIC and its
fix, and the second-commit rule solves every one of them.
[SZZ-0212](../SZZ-0212/README.md) made that shape discriminating with a
two-commit oracle and a single whitespace-only hop. This one is a step deeper:
**two** rewrites separate the first fault from the fix, of two different kinds —
a comparison extracted into a named local, then that local renamed — so no
blame variant shortens the walk and a tool has to follow the line twice.

## Commit structure

```text
c0  Add the request quota check          allowed: used < quota; remaining: quota - used
c1  Let a client reach its quota exactly  used <= quota                                    <- BIC
c2  Name the quota comparison             the comparison becomes a local, underQuota       (rewrite)
c3  Say within rather than under in the quota check   underQuota renamed to withinQuota    (rewrite)
c4  Rework the remaining count            quota - used - 1                                 <- BIC
c5  Stop a client at its quota and report the full remainder                               <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c4` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c5`

`c2` and `c3` change no behaviour; they only move who owns the line.

## Measured behaviour

`allowed(used, 10)` for 9, 10 and 11 used requests, and `remaining(used, 10)`
for 3 and 10, at each commit (`tests/test_largest_pockets.py`):

| commit | allowed 9 | allowed 10 | allowed 11 | remaining(3) | remaining(10) |
|---|---|---|---|---|---|
| `c0` | T | F | F | 7 | 0 |
| `c1` | T | **T** | F | 7 | 0 |
| `c2` | T | T | F | 7 | 0 |
| `c3` | T | T | F | 7 | 0 |
| `c4` | T | T | F | **6** | **-1** |
| `c5` | T | F | F | 7 | 0 |

`c2` and `c3` move nothing. The two faults are independent, and the partial fix
at `c4` shows both are needed.

## Measured blame outcome at BFC^

The fix deletes two lines:

```text
"boolean withinQuota = used <= quota;"   plain -> c3   -w -> c3   -w -C -C -> c3
"return quota - used - 1;"               plain -> c4   -w -> c4   -w -C -C -> c4
```

Blame returns `{c3, c4}`: `c4` is right, `c3` is the rename, and `c1` is two
steps further back along the line's history. Neither `-w` nor `-C` helps,
because both rewrites changed tokens: `c2` replaced an expression with a named
local and `c3` renamed that local.

## What a tool must do to pass

Report exactly `{c1, c4}`. Recursion has to run twice from `c3` — past the
rename to `c2`, and past the extraction to `c1` — and both `c2` and `c3` have
to be rejected on the way, since each changed tokens without changing an
answer.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

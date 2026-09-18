# SZZG-0119: A move that inlines two named conditions takes ownership of an earlier fault

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. It is the
third instance of the *rewrite* kind — after
[SZZ-0192](../../scenarios/SZZ-0192/README.md) (extract variable) and
[SZZ-0197](../../scenarios/SZZ-0197/README.md) (extract method) — and the first
that **inlines** rather than extracts, while moving the file at the same time.

## Commit structure

```text
c0  Add the paging test                       two named locals: >= pageStart, < pageStart + pageSize
c1  Start each page after its first index     atOrAfterStart = index > pageStart              <- BIC
c2  Move the pager into its own package and inline the bounds   one expression, new package   (rewrite)
c3  Let a page reach the index one past its size   index <= pageStart + pageSize              <- BIC
c4  Page from the first index up to the page size  both bounds restored                       <- BFC
```

`c2` moves `example.Pager` to `example.paging.Pager` and replaces the two named
locals with a single expression. `c3` then edits that expression, so by the
time the fix runs, the line carrying **both** bounds was last written by `c3`
and `c1` is on no line that still exists.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`exact_set`, `required: [c1, c3]`)
- BFC: `c4`

## Measured behaviour (from the generated repository)

13824 argument triples, compared by method and arguments with the package name
stripped so the move does not look like a change:

```text
c0  Add the paging test                       13824 probes
c1  Start each page after its first index     379 answers change
c2  Move the pager into its own package and inline the bounds   0 answers change  <- behaviour-preserving
c3  Let a page reach the index one past its size   62 answers change
c4  Page from the first index up to the page size  441 answers change
```

`441 = 379 + 62`: the fix restores exactly the union of the two faults, and
neither fault overlaps the other.

## Measured history shape

The inline leaves the moved file only **36% similar** to its source, below
git's default rename threshold of 50%, so the move is not recorded as a rename
at the default setting:

```text
git log --follow -- src/main/java/example/paging/Pager.java
  23f1c3b Page from the first index up to the page size
  4d4b648 Let a page reach the index one past its size
  cdf76af Move the pager into its own package and inline the bounds     <- stops here

git log --follow --find-renames=20% -- src/main/java/example/paging/Pager.java
  ... and then 60556b9 Start each page after its first index, 99f7159 Add the paging test
```

So a tool that walks the fixed file's history with git's defaults never lists
`c1`. Reaching it takes a deliberately lowered similarity threshold — the same
obstacle a real move-plus-rewrite presents.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return index > pageStart && index <= pageStart + pageSize;"
    plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}` — half the answer. `c1` is not reachable from the deleted
line by any blame variant, and copy detection does not rescue it, because the
inlined expression is new text rather than a copy of either local.

## What a tool must do to pass

Report exactly `{c1, c3}`, and not `c2`, which changed no behaviour. Reaching
`c1` needs the move to be followed across a sub-threshold similarity *and* the
inlined expression to be related back to the local it replaced.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

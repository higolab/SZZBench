# SZZG-0109: File deletion

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `file-deletion` |
| oracle | `exact_set`; required `c0`; related but not correct `c1`, `c3` · BFC `c4` |
| graph features | operation `delete_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ traces a **deletion-based fix** back to the commit that wrote the
faulty line. The BFC removes the whole faulty file, so deleted-line blame covers every
line of that file, not just the faulty one, and the tool has to choose among the commits
those lines reach.

Before this repair the scenario had only two commits, so `c0` was the only possible answer
and nothing could be discriminated (issue #4).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the value filter interface, the legacy range filter and the registry
    (ValueFilter.java, LegacyRangeFilter.java with the faulty `value > min && value < max`,
     FilterRegistry.java handing out the legacy filter)          <- BIC
c1  Include the filter id in the legacy filter description       (touches the file that will be deleted)
c2  Add the interval filter for the new ingest pipeline          (IntervalFilter.java, inclusive)
c3  Reject inverted intervals in the filter registry             (touches the registry method the BFC edits)
c4  Remove the legacy range filter, which excluded the interval bounds   <- BFC
    (deletes LegacyRangeFilter.java and switches the registry to IntervalFilter)
```

## Expected BIC / BFC

- BIC: `c0` (`expected_szz.commit_level.required = [c0]`, policy `exact_set`)
- BFC: `c4`
- `related_but_not_correct`: `c1` (rewrote one of the deleted lines), `c3` (rewrote the
  registry method the BFC edits)

## Measured plain-blame outcome at BFC^

`BFC^` is `c3`. The BFC deletes 21 lines: the registry line
`return new LegacyRangeFilter(min, max);` and all 20 lines of `LegacyRangeFilter.java`.
Blaming each deleted line at `BFC^` gives:

```text
FilterRegistry.java:8       "return new LegacyRangeFilter(min, max);"   -> c0
LegacyRangeFilter.java:1-17 (incl. "return value > min && value < max;") -> c0
LegacyRangeFilter.java:18   "return \"legacy-range:\" + min + \":\" + max;" -> c1
LegacyRangeFilter.java:19-20                                             -> c0
```

Outcome: **extra**. Plain blame over the deleted lines returns `{c0, c1}`; the required set
is `{c0}`, so `c1` is an extra (false-positive) commit. Restricted to the faulty line alone
the outcome is exact (`c0`), which is what the generator's verification measures (`GI703`).
`c3` is not reached by deleted-line blame, but a file- or method-level tool reaches it
through the registry, which is why it is listed in `related_but_not_correct`.

## What a tool must do to pass

- Handle a fix that consists of deleting a file at all (no "modified line" pair exists).
- Report exactly `{c0}`: pick the commit that wrote the *faulty* line out of the commits
  that the deleted lines reach, instead of returning every commit that ever touched the
  deleted file (`c1`) or the rewritten registry method (`c3`).

## Behaviour check (measured)

The faulty file is gone at the BFC, so the initial and BFC snapshots cannot be compared on
`LegacyRangeFilter` itself. The contract tested instead is the shared public API
`FilterRegistry.filterFor(min, max).accepts(value)`, which exists in every snapshot:

- inputs: values `{MIN_VALUE, MIN_VALUE+1, -6, -5, -4, -1, 0, 1, 6, 7, 8, 9, 10, 11, MAX_VALUE-1, MAX_VALUE}`
  against the intervals `(0,10)`, `(-5,5)`, `(7,7)`, `(MIN_VALUE,MAX_VALUE)`, `(MIN_VALUE,0)`,
  `(0,MAX_VALUE)` (96 probes), plus one inverted interval `(5,1)`.
- `c1` and `c2` are behaviour-identical to `c0` on all 96 probes.
- `c3` differs only for the inverted interval, which it now rejects (`IllegalArgumentException`).
- `c4` (BFC) differs from `c0` exactly on the 10 boundary inputs, which the bug rejected and
  the fix accepts, and agrees with `c0` on the other 86 probes.

Because the bug exists from the initial commit (`c0` *is* the BIC), there is no earlier
correct snapshot the BFC could be compared against; the contract above is the restored one.

## Category note (issue #4)

The repaired scenario is about the *shape of the fix* (a fix by removing code) and about
choosing among the commits that the deleted lines reach. That is not a non-source, binary,
generated or scalability property, so **G8 fits only loosely**; a fix-shape category (G1 /
the classic "BFC shape" family) would fit better. The category code is kept unchanged here
because re-categorization is a separate decision.

## Required graph-schema features

- Factors: delete_file
- Operation types: write_file, replace, delete_file
- Expected SZZ policy is defined in `expected_szz`.

---

## Files

```text
SZZG-0109/
|-- scenario.graph.yml
`-- README.md
```

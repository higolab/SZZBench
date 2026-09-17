# SZZ-0130: Field extraction after BIC

## Purpose

A repeated literal is extracted into a private constant between the BIC and
the BFC. The extraction rewrites the faulty line (`50` becomes
`MAX_FILES_PER_BATCH`), so the line the bug-fixing commit deletes was last
written by the refactoring commit and plain `git blame` misses the BIC. The
BFC repairs the comparison and **keeps the constant**.

Two defects of the previous version are repaired: the code did not compile
(the identifier `limit` was never declared, so javac failed at c0, c1 and
c3 — issue #10), and the BFC restored the initial file text, which deleted
the extracted constant again and made a textbook SZZ return `{c1, c2}`
(issue #6).

## Commit structure

- `c0`: Adds `BatchUploadQuota` with `remainingSlots(uploadedFiles)` and
  `acceptsMore(uploadedFiles)`; both repeat the literal batch size `50`.
- `c1`: Accepts a file while the batch reports zero free slots
  (`50 - uploadedFiles >= 0`), so a full batch takes one file too many.
  This is the BIC.
- `c2`: Extracts the literal into
  `private static final int MAX_FILES_PER_BATCH = 50;` and uses it in both
  methods. Behaviour-preserving; the faulty line is rewritten.
- `c3`: Makes the comparison strict again, using the constant. This is the
  BFC; its diff is `+1 −1` in one hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor: it is what basic blame returns, but it did not introduce
the fault.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`return MAX_FILES_PER_BATCH - uploadedFiles >= 0;` — the constant
declaration that `c2` added is *not* deleted. `git blame` at `c3^` on the
deleted line returns **`c2`**, so the outcome is **miss**. Measured
variants on that line: `git blame -M`, `-C`, `-C -C`, `-w`, `-w -M` and
`-w -C -C` all return **`c2`** as well — unlike in SZZ-0128, the line
differs in more than whitespace, so no built-in git heuristic recovers the
BIC; `git log -L 17,17:<file>` likewise stops at `c2` first.
`szzbench generate` reports the informational finding
`W700: basic git blame reaches <c2>, not expected BIC(s) ['c1']`, which is
the designed property of the scenario (as in SZZ-0081 and SZZ-0178).

## What a tool must do

To pass, a tool has to walk the line history one step further (the line
`c2` replaced was written by `c1`) or to recognise the extract-constant
refactoring as behaviour-preserving and continue to `c1`, where the faulty
comparison `uploadedFiles >= 0` first appears. Returning `{c1, c2}` counts
as a false positive (`false_positives_allowed: []`).

## Behaviour check

`remainingSlots` and `acceptsMore` keep their signatures in all snapshots
and were probed over
`uploadedFiles ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -50, -1, 0, 1, 25, 48, 49, 50, 51, 52, 100, MAX_VALUE-1, MAX_VALUE}`
(15 inputs, including the values where `50 - uploadedFiles` overflows).
`c1` differs from `c0` in exactly one case, `uploadedFiles == 50` (the full
batch), `c2` reproduces `c1` exactly (the extraction is
behaviour-preserving), and `c3` agrees with `c0` on all 15 inputs.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `field-extraction-after-bic`
- `basic-blame-distractor`

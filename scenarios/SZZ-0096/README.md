# SZZ-0096: Lambda rewrite after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `lambda-rewrite-after-bic`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks how SZZ implementations behave when a behaviour-preserving
refactoring between the BIC and the BFC moves the faulty predicate from an `if`
statement into a lambda. The bug-fixing commit repairs the predicate *in the
lambda*; it does not undo the refactoring, and the import the refactoring added
stays in place.

## Commit structure

- `c0`: Adds `MembershipStats.adultCount(int[])`, a counting loop with
  `if (age >= MIN_AGE)` and `MIN_AGE == 18`.
- `c1`: Changes the predicate to `age > MIN_AGE`, so members of exactly 18 are no
  longer counted. This is the BIC.
- `c2`: Replaces the loop with
  `return (int) IntStream.of(ages).filter(age -> age > MIN_AGE).count();` and adds
  the `java.util.stream.IntStream` import. The rewrite is behaviour-preserving
  with respect to `c1`.
- `c3`: Changes the lambda's predicate to `age >= MIN_AGE`. This is the BFC. Its
  first-parent diff is `+1 -1` on a single line; the import stays.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (the stream statement). `git blame` at
`c3^` on that line returns **`c2`**: plain blame **misses** the BIC. `git blame -w`
does not help, because `c2` is not a whitespace-only change.

## What a tool must do

To pass, a tool has to follow the line history past the refactoring: one step
back from `c2`, the same predicate is the `if` condition written by `c1`.
Recognising `c2` as a loop-to-stream rewrite, or searching the history for the
predicate `age > MIN_AGE` (`git log -S`), both lead to `c1`.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`.
- Behaviour probe over 13 fixed arrays (empty, `{17}`, `{18}`, `{19}`, `{0}`,
  `{-1}`, `{17,18}`, `{18,18,18}`, `{16,…,20}`, `{Integer.MIN_VALUE}`,
  `{Integer.MAX_VALUE}` and two mixed arrays containing both extremes), the 46
  single-element arrays for ages `-5`…`40`, and one 10 000-element array built
  from a repeating `-5`…`35` pattern — 60 outputs in total. The `c1` snapshot
  differs from `c0` for every input that contains an age of exactly 18; the `c3`
  snapshot agrees with `c0` on every probed input.

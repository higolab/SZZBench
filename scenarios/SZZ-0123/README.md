# SZZ-0123: BFC with two faulty expressions fixed

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `single-line-bfc`, `two-faulty-expressions`, `statement-granularity` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks the *granularity* at which a tool reports a fault. The
bug-fixing commit repairs **two faulty expressions that sit on one line**:
`value > min` and `value < max`. Commit-level SZZ sees a single deleted
line; a line-level oracle sees one faulty statement; only an
expression-level report distinguishes the two comparisons. The BFC is a
single hunk of one deleted and one added line — it is *not* a multi-line
fix, which is why the former factor `multiple-line-bfc` was wrong
(issue #5).

## Commit structure

- `c0`: Adds `Scenario0123.contains(value, min, max)` with the inclusive
  range check `value >= min && value <= max`.
- `c1`: Turns both bounds into strict comparisons
  (`value > min && value < max`), so both ends of the range are rejected.
  This is the BIC.
- `c2`: Restores both comparisons in the same line. This is the BFC.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. There is no
intermediate commit and no distractor.

## Plain blame outcome (measured)

`git diff -U0 c2^ c2` deletes exactly one line,
`return value > min && value < max;`, in one hunk. `git blame` at `c2^` on
that line returns **`c1`**: the outcome is **exact** — the required BIC set
`{c1}` is reached with no extra candidate. `git blame -C -C` returns `c1`
as well.

## What a tool must do

Commit-level: return `{c1}` — trivially reachable with basic blame, so the
scenario is a control at that level. Line-level: report the single deleted
line. Expression-level: report *both* faulty comparisons; reporting only
one of them is an incomplete fault localisation even though the commit-level
answer is right.

## Behaviour check

`contains` was probed over 1600 combinations of
`value ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -11, -10, -9, -1, 0, 1, 4, 5, 6, 9, 10, 11, MAX_VALUE-1, MAX_VALUE}`
and `min`, `max ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -10, -1, 0, 1, 5, 10, MAX_VALUE-1, MAX_VALUE}`:
`c1` differs from `c0` in 100 of them (exactly the cases in which `value`
sits on a bound), and `c2` agrees with `c0` in all 1600.

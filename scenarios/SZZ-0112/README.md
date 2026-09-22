# SZZ-0112: Huge method surrounding small bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `robustness`, `large-method`, `small-fault` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

A one-token fault sits in the middle of a genuinely large method:
`TransactionRiskScorer.score(...)` is 73 lines long, has seven parameters
and applies ten rules built from eighteen constants. The BIC and the BFC
each touch exactly one line of it. The scenario tests whether a tool stays
line-precise when the enclosing entity is large — a method-level or
entity-level attribution would mark the whole method, and a tool that
reports "the method changed" instead of "this line changed" cannot
distinguish the fault from the 72 untouched lines.

Before this revision the "huge" method had 14 generated filler statements
(`int tmp1 = value + 1; ...`) and mis-indented ones at that, which did not
support the title (issue #5).

## Commit structure

- `c0`: Adds `TransactionRiskScorer` with the 73-line `score(...)` method and
  the derived `declines(...)`.
- `c1`: Changes the velocity rule from `>=` to `>`
  (`transactionsLastHour > SUSPICIOUS_TRANSACTIONS_PER_HOUR`), so the fifth
  transaction within an hour no longer scores the velocity penalty. This is
  the BIC. It is line 75 of 131, and line 30 of the method.
- `c2`: Restores `>=`. This is the BFC.

There is no intermediate commit: the noise of this scenario is *contextual*
(a large surrounding method), not historical.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Plain blame outcome (measured)

`git diff -U0 c2^ c2` deletes exactly one line (one hunk, `+1 −1`). `git
blame` at `c2^` on that line returns **`c1`**: the outcome is **exact**, and
`git blame -C -C` returns `c1` as well. No distractor commit exists, so a
line-level tool cannot fail unless it widens the fault to the enclosing
method or file.

## What a tool must do

Return `{c1}` and, at line level, exactly the deleted line. The scenario
also serves as a scale check: the surrounding 72 lines of the same method
are old (`c0`) and must not be reported.

## Behaviour check

`score(...)` and `declines(...)` were probed over 26 880 input combinations:
`amountCents ∈ {0, 1, 249999, 250000, 999999, 1000000, Integer.MAX_VALUE}`,
`accountAgeDays ∈ {0, 6, 7, 29, 30, 364, 365, Integer.MAX_VALUE}`,
`failedLogins ∈ {0, 2, 3, 10}`,
`transactionsLastHour ∈ {0, 1, 4, 5, 6, Integer.MAX_VALUE}`,
`hourOfDay ∈ {0, 5, 6, 22, 23}`, `newDevice` and `foreignCountry` both
boolean. `c1` differs from `c0` in 4392 of them (every input with
`transactionsLastHour == 5`, including cases in which the decline decision
itself flips), and `c2` agrees with `c0` in all 26 880.

## Category note

The scenario stays in `S3` (`category_code` is stable), but S3 is
"intermediate noise and history noise" and this history has no intermediate
commit. S4 ("BFC-side noise and tangled commits") would not be a better
home either: neither the BIC nor the BFC is tangled — both are single-line
commits. What the scenario really varies is the *size of the surrounding
entity*, which is a robustness/scale factor rather than a history factor.

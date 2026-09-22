# SZZ-0187: BFC touching three files with a single BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `multi-file-bfc`, `three-file-bfc`, `caller-update-in-bfc` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

None of the existing BFCs touches three or more files. This scenario adds a
BFC that modifies three *existing* files. The fault is a contract change in
one class (`DiscountPolicy.rate()` starts returning a fraction instead of a
percentage) whose two callers were not updated; the fix renames the method
to make the unit explicit and rewrites both call sites. Only one of the three
hunks blames the BIC; the two caller hunks blame the initial commit, so a
tool that returns the blame of every deleted line reports the initial commit
as a second candidate.

## Commit structure

- `c0`: Adds `Customer`, `DiscountPolicy` (`int rate(Customer)` returning a
  percentage), `CheckoutService.payableCents(...)` and
  `QuoteBuilder.line(...)`; both callers compute `(100 - rate) / 100.0`.
- `c1`: Changes `DiscountPolicy` to store and return a fraction
  (`double rate(Customer)`, e.g. `0.10`) without touching the callers, so a
  10 % member discount becomes a 0.1 % discount. This is the BIC.
- `c2`: Changes the customer-id decoration in `QuoteBuilder.line` from
  parentheses to brackets. Unrelated to the fault.
- `c3`: Renames `rate` to `discountFraction` and rewrites both call sites to
  `Math.round(... * (1 - fraction))`. This is the BFC. Its diff is `+5 -5`
  across three files (`DiscountPolicy.java` `+1 -1`, `CheckoutService.java`
  `+2 -2`, `QuoteBuilder.java` `+2 -2`).

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c0` is
not a BIC: its call sites were correct for the percentage contract that
existed when they were written.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes five lines in three files. `git blame` at
`c3^` returns **`c1`** for the line in `DiscountPolicy.java` and **`c0`** for
the four caller lines in `CheckoutService.java` and `QuoteBuilder.java`: the
BIC is reached, with one extra candidate.

## What a tool must do

To pass, a tool must not take the union of the per-file blame results. It
has to recognise that the caller hunks are consequences of the
`DiscountPolicy` change (the renamed method forces every caller to change),
or rank the candidates so that the commit that changed the callee's
semantics outranks the commit that wrote the callers, e.g. by scoring per
hunk, by preferring the hunk in the file named by the changed API, or by
noticing that `c0` is the initial commit of the repository and that the
caller hunks only adapt to an API change.

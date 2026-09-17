# SZZ-0188: Fault in a multi-line statement whose lines come from different commits

## Purpose

This scenario separates *line* granularity from *statement* granularity. The
faulty code is a single `return` statement spread over four lines; the BIC
added one of those lines, the other three come from the initial commit. The
fix changes two lines of the statement, one from each origin. Blame of the
deleted lines therefore returns two commits with equal standing; only
reasoning about the statement (which edit changed its meaning) singles out
the BIC.

## Commit structure

- `c0`: Adds `Request` and `AccessPolicy.isAllowed(...)`, whose return
  statement is `authenticated && hasRole && !suspended`, one operand per
  line.
- `c1`: Inserts the line `|| request.isInternal()` between the `hasRole`
  and `isSuspended` lines (`+1 -0`). Because `&&` binds tighter than `||`,
  the statement now reads `(authenticated && hasRole) || (internal &&
  !suspended)`, so an unauthenticated internal request is allowed. This is
  the BIC.
- `c2`: Adds `Request.getUserId()`. Unrelated to the fault.
- `c3`: Adds parentheses around `hasRole || isInternal`, changing the `c0`
  line `&& request.hasRole(requiredRole)` and the `c1` line
  `|| request.isInternal()`. This is the BFC. Its diff is `+2 -2` in one
  hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c0` is
not a BIC: the statement it wrote was correct until `c1` extended it.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes two adjacent lines. `git blame` at `c3^`
returns **`c0`** for `&& request.hasRole(requiredRole)` and **`c1`** for
`|| request.isInternal()`: the BIC is reached, with one extra candidate.

## What a tool must do

To pass, a tool must work at statement level: identify the whole `return`
statement as the fixed unit, collect the commits that edited it (`c0`
created it, `c1` extended it) and decide which edit introduced the fault.
Comparing the statement before and after `c1` (the added `||` operand
changes the evaluation of the whole expression) selects `c1`; the `c0` line
changed in the fix only because the opening parenthesis had to be placed
there. Note that the BIC's own diff is addition-only (`+1 -0`), so matching
deleted fix lines against added BIC lines succeeds only for the `isInternal`
line.

## Factors

- `single-bic`
- `single-bfc`
- `line-addition-bic`
- `multi-line-statement`
- `statement-granularity`
- `operator-precedence`

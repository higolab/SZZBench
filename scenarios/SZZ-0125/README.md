# SZZ-0125: Method rename after BIC

## Purpose

A method is renamed between the BIC and the BFC. The rename rewrites the
signature and the call site, but **not the faulty line inside the method
body**, so the line the BFC deletes is still the one the BIC wrote. This
makes the scenario an honest **control**: a refactoring sits in the history,
yet plain `git blame` reaches the BIC. It is the matched control for
SZZ-0124 (variable rename that *does* rewrite the faulty line, blame class
`miss`); together the two show that "a refactoring happened after the BIC"
is not by itself a difficulty — what matters is whether the refactoring
touched the faulty line.

The previous version let the BFC restore the pre-rename text and so undid
the rename (issue #6); a textbook SZZ then returned `{c1, c2}` for a reason
that had nothing to do with the rename. The BFC now keeps the new method
name.

## Commit structure

- `c0`: Adds `SessionPolicy` with the public `isAlive(...)` /
  `remainingMinutes(...)` and the private helper `withinTimeout`, which
  accepts a session up to and including the idle timeout.
- `c1`: Makes the comparison strict (`idleMinutes < idleTimeoutMinutes`), so
  a session is dropped at exactly the timeout. This is the BIC.
- `c2`: Renames `withinTimeout` to `isWithinIdleTimeout` (declaration and
  call site, two lines). Behaviour-preserving; the faulty line in the body
  is untouched.
- `c3`: Restores the inclusive comparison **inside the renamed method**.
  This is the BFC; its diff is `+1 −1` in one hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
listed as a known distractor, but basic blame does not even return it.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`return idleMinutes < idleTimeoutMinutes;` — no line added by `c2` is
deleted. `git blame` at `c3^` on that line returns **`c1`**: the outcome is
**exact** (no extra candidate, nothing missed), and `git blame -C -C`
returns `c1` as well. `szzbench generate` reports `I700` (basic blame
reaches the expected BIC).

## What a tool must do

Return `{c1}`. Basic blame is sufficient; the scenario checks that a
refactoring-aware tool does not *over*-shoot, e.g. by adding the renaming
commit `c2` to the answer just because a refactoring detector reports a
rename in the same file between BIC and BFC.

## Behaviour check

The public methods `isAlive(idleMinutes, revoked)` and
`remainingMinutes(idleMinutes)` were probed over 132 input combinations:
`idleTimeoutMinutes ∈ {Integer.MIN_VALUE, 0, 1, 15, 30, Integer.MAX_VALUE}`
(constructor), `idleMinutes ∈ {Integer.MIN_VALUE, -1, 0, 1, 14, 15, 16, 29, 30, 31, Integer.MAX_VALUE}`
and `revoked ∈ {false, true}`. `c1` differs from `c0` in exactly the 6 cases
in which `idleMinutes == idleTimeoutMinutes` and the session is not revoked;
`c3` agrees with `c0` in all 132. The rename of `c2` is private and does not
change the public API.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `method-rename-after-bic`
- `matched-control`

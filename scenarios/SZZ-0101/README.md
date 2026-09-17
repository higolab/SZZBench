# SZZ-0101: Throws declaration after BIC

## Purpose

This scenario checks that an intermediate, purely declarative signature change
between the BIC and the BFC does not disturb bug-introducing-commit
identification. The intermediate commit adds a `throws` clause to a
*neighbouring* method and touches nothing else, so the faulty line survives
unchanged from the BIC to the BFC parent.

It is an honest **control**: plain `git blame` solves it. It is included so
that a tool which reports extra candidates whenever the fault's file changed
after the BIC can be distinguished from one that follows the faulty line.

## Commit structure

- `c0`: Adds `com.example.config.ConfigLoader` with `hasProfile(String)`
  (`return requested != null;`) and `resolveProfile(String)`, which returns the
  requested profile when one was given, falls back to the default profile, and
  throws `IllegalStateException` when no default profile was configured.
- `c1`: Inverts the check in `hasProfile` to `return requested == null;`.
  This is the **BIC**. `resolveProfile` now returns the caller's `null` and
  falls back to the default for every name that was actually supplied.
- `c2`: Adds `throws IllegalStateException` to the signature of
  `resolveProfile`. Declaration only; no statement changes, and in particular
  the faulty line in `hasProfile` is not touched.
- `c3`: Restores `return requested != null;`. This is the **BFC**; its
  first-parent diff is `+1 -1` on that one line.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return requested == null;` (line 11). `git blame` and `git blame -w`
at `c3^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Blame the deleted line and stop. The only way to fail is to add `c2` because
it is the most recent commit on the file, or because its signature change
overlaps the enclosing class.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `throws-after-bic`

# SZZ-0104: Method order change after BIC

## Purpose

This scenario checks that a change to the *declaration order* of methods
between the BIC and the BFC does not disturb bug-introducing-commit
identification. The class holds three methods from `c0` on; the intermediate
commit moves one of them and adds, removes and rewrites nothing.

It is an honest **control**: plain `git blame` solves it. Its value is to show
what `git blame` does with a moved block, which is easy to get wrong in a
heuristic: blame follows *content lines*, not methods, so the moved method is
re-attributed to the commit that moved it, while every line that stayed where
it was keeps its original commit.

## Commit structure

- `c0`: Adds `com.example.pricing.DiscountTable` with, in this order,
  `qualifies(int, int)` (`return quantity >= threshold;`), `tierFor(int)` and
  `percentFor(int)`.
- `c1`: Changes the comparison to `return quantity > threshold;`. This is the
  **BIC**: an order of exactly the threshold quantity no longer qualifies.
- `c2`: Moves `percentFor` in front of `tierFor`, so the order becomes
  `qualifies`, `percentFor`, `tierFor`. Its diff is `+4 -4`; the moved block is
  byte-identical and no statement changes.
- `c3`: Restores `quantity >= threshold`. This is the **BFC**; its first-parent
  diff is `+1 -1`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return quantity > threshold;` (line 5). `git blame` and
`git blame -w` at `c3^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

Measured side observation, recorded because it is the point of the scenario:
`git blame` at `c2` attributes the four lines of the moved `percentFor` block
to `c2` (they count as newly inserted content at their new position), while
lines 1-7 and 12-21, including the faulty line 5, still point at `c0`/`c1`.
Plain blame would therefore have reported `c2` if the *faulty* method had been
the one that moved; here it is not.

## What a tool must do

Blame the deleted line and stop. A tool fails by adding `c2`, for example
because `c2` is the most recent commit on the file, or because a method-level
(rather than line-level) change model sees "the method list of `DiscountTable`
changed" and treats the whole class as touched.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `method-order-change-after-bic`

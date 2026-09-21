# SZZG-0136: The fault predates the repository: an import commit is the history's boundary, not the BIC

## Purpose

The second contract for "the fix's deleted line belongs to the first commit"
(issue #24). The first commit imports a billing module from another version
control system and says so twice: its message names the source repository and
revision (`accounting SVN, r4120`) and `docs/IMPORT.md`, written by the same
commit, records that the earlier history is not part of this repository. The
imported code already carries the fault. The introducing change therefore lies
before the boundary, and the default oracle is the empty set; the variant
`boundary-commit` accepts `c0` for a tool that reports the boundary *as a
boundary*. The twin [SZZG-0137](../SZZG-0137/README.md) is the same code and
history with an authored first commit — there `c0` is the BIC. Contract:
[origin-direct-contract.md](../../docs/decisions/origin-direct-contract.md), D11.

## Commit structure (generated, every author and date pinned)

```text
* 0e78bbe  2024-01-29  Charge only the days beyond the grace period                       <- BFC (c3)
* a7b8e44  2024-01-22  Record the report about late fees charged from the first day        (c2, writes docs/issues/ISSUE-8.md)
* b574573  2024-01-15  Add the invoice reminder text                                      (c1, unrelated)
* f780278  2024-01-08  Import the billing module from the accounting SVN repository (r4120) (c0, boundary; writes docs/IMPORT.md)
```

## Expected BIC / BFC

- default: none — `expect_no_bic: true`; `known_distractors: [c0]`
- variant `boundary-commit`: `required: [c0]` (`exact_set`)
- BFC: `c3`

## Measured behaviour, blame and twin identity

`feeCents(5, 3, 100)` is **500** at `c0`, `c1`, `c2` and **200** at `c3`;
`feeCents(3, 3, 100)` is 0 throughout (the grace-day guard was always right).
Blaming line 13 of `LateFee.java` (`return daysLate * centsPerDay;`) at `c3^`
returns `c0`, and `git blame` prints it with a `^` prefix — Git's own marker for
a *boundary commit*, the same word this scenario uses for it.

Against SZZG-0137, `tests/test_policy_families.py` checks: `c1`, `c2`, `c3` have
identical message, author and dates; `c0` has the same author and date and a
different message; the `HEAD` trees are identical except that this repository
has `docs/IMPORT.md`. The provenance evidence is the only difference between the
twins, and it is what flips the oracle.

## What a tool must do

Under the default oracle, report nothing: the commit that wrote the faulty line is
not in this repository, and `c0` merely brought it in. A tool that cannot tell an
import from an authored commit will report `c0`, exactly as in SZZG-0137; a tool
that reads the import message or `docs/IMPORT.md` can either abstain or report
`c0` labelled as the history boundary, which the `boundary-commit` variant
accepts.

## Factors

- `expect-no-bic`
- `history-boundary`
- `import-commit`
- `tool-visible-context`
- `evaluation-variant`
- `single-bfc`

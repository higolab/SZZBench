# SZZ-0198: A guard that substitutes a different value, and a later caller that reaches it

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. The
unreachable commit changed **what a guard substitutes**, not whether the guard
is there — where [SZZ-0193](../SZZ-0193/README.md) deletes a guard, here the
guard survives and answers differently, and the fault appears when a later
commit first sends an argument into it.

It is also the first two-commit-oracle scenario whose fault file is touched by
**no other commit before the fix**: `fault_file_distractors` is 0, so the
history offers nothing local to mistake for the answer.

## Commit structure

```text
c0  Add the retry policy                        attemptsFor() floors at 0; attemptsForJob() clamps its argument
c1  Always allow at least one attempt           the floor becomes 1                          <- BIC
c2  Record what the retry policy promises       class comment only (distractor)
c3  Report how many attempts a job has left     new file: remainingAttempts() subtracts      <- BIC
c4  Report no attempts left once they are used up  used >= configured ? 0 : ...              <- BFC
```

`c1` raises the floor the policy returns for a non-positive request. The only
caller in the repository, `attemptsForJob`, clamps its argument to at least 1,
so it cannot observe the change. `c3` adds a caller that *subtracts*, so a
non-positive request reaches the policy for the first time and a job with no
attempts left is told it has one.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

## Measured behaviour (from the generated repository)

```text
c0  Add the retry policy                        16 probes
c1  Always allow at least one attempt           3 change: attemptsFor(-2,-1,0): 0 -> 1
                                                attemptsForJob is unchanged at every argument
c2  Record what the retry policy promises       0 change
c3  Report how many attempts a job has left     30 keys appear, 0 change
c4  Report no attempts left once they are used up  20 change
```

`c1` is not behaviour-preserving in the narrow sense — `attemptsFor` is public
and its answers below the floor do change — but no *caller in the repository*
can see it, which is what keeps it out of reach of the fix.

**Both commits are necessary, measured rather than argued.** Reverting `c1` on
top of `c3` — the tree in which the faulty caller exists but the raised floor
does not — reproduces the fixed behaviour on **all 30** `remainingAttempts`
arguments, with none disagreeing:

```text
                       remainingAttempts(3,3)   remainingAttempts(3,5)
c3 as shipped          1                        1        <- the bug: attempts never run out
c3 with c1 reverted    0                        0
c4 (the fix)           0                        0
```

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return policy.attemptsFor(configured - used);"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching `c1` means following the call in the fixed
line into `RetryPolicy.attemptsFor`, recognising that the subtraction can enter
its guarded branch, and finding the commit that changed what that branch
returns.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

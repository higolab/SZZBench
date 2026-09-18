# SZZG-0098: Only commit message provides the clue

## Source

- Category: Issue, message, context, and non-local evidence (G7)

## Purpose

Evaluate whether a context-aware SZZ method can use **commit-message** evidence when a
behaviour-preserving refactor has deleted the faulty line *together with an equally shaped
line written by an innocent commit*, so that no line-level evidence separates the two
candidates.

Two repairs led to the current history:

* the original scenario had plain blame reaching the BIC directly, a meaningless
  `region.length() == 2` test and a thrice-repeated fault statement (issue #4);
* the first repair moved the faulty line into a `switch` **without changing its text**, so
  `git blame -w` recovered `c1` immediately and the message clue was still not required
  (PR #33 review finding 1). The refactor now *deletes* the line instead of re-indenting it.

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the regional checkout challenge gate
    EU -> return true;  CA -> return true;  else -> riskScore >= HIGH_RISK_SCORE
c1  PAY-314 bypass the EU checkout challenge while the consent copy rolls out   <- BIC
    the EU branch becomes `return merchantRiskFlag;`
c2  PAY-330 let Canadian merchants below the risk score skip the checkout challenge
    the CA branch becomes `return merchantRiskFlag || riskScore >= HIGH_RISK_SCORE;`
    a deliberate product change, the same relaxation in the same shape -> the rival candidate
c3  PAY-352 collapse the two regional gates into one branch     behaviour-preserving refactor
    both branches become `if (region.equals("EU") || region.equals("CA"))` with one
    merged expression; the patch deletes the line c1 wrote and the line c2 wrote
c4  PAY-501 require the checkout challenge for EU orders again                  <- BFC
    the merged expression gains the `region.equals("EU") ||` disjunct
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c4`
- `related_but_not_correct`: `c2` (the equally shaped Canadian relaxation) and `c3` (the
  commit blame actually reaches)

## Measured blame outcome at BFC^

`BFC^` is `c3`. The BFC modifies exactly one line, line 8 of
`src/main/java/example/CheckoutChallengeGate.java`:

```text
"    return merchantRiskFlag || (region.equals("CA") && riskScore >= HIGH_RISK_SCORE);"
```

Blame of that line at `c3`, measured in the generated repository:

| variant | result |
|---|---|
| `git blame` | `c3` |
| `git blame -w` | `c3` |
| `git blame -w -M` | `c3` |
| `git blame -w -C -C` | `c3` |

Outcome: **miss** under every variant — the whitespace-insensitive and copy/move-aware
blames no longer recover `c1`, because the line it wrote does not exist at `BFC^` any more.

One hop further back does not disambiguate either. The lines `c3` deletes blame, at `c3^`, to

```text
CheckoutChallengeGate.java:7   if (region.equals("EU")) {                                   -> c0
CheckoutChallengeGate.java:8     return merchantRiskFlag;                                   -> c1
CheckoutChallengeGate.java:9   }                                                            -> c0
CheckoutChallengeGate.java:10  if (region.equals("CA")) {                                   -> c0
CheckoutChallengeGate.java:11    return merchantRiskFlag || riskScore >= HIGH_RISK_SCORE;   -> c2
```

so the candidate set that line history yields is `{c1, c2}` plus the structural lines of
`c0`. Both candidates relax the same challenge in the same way; the code does not say which
region regressed.

Because the fault statement is no longer present at `BFC^`, generation reports

```text
[WARNING] GW701: bug B001: fault.statement not present in final BFC parent; basic blame unavailable.
```

instead of the earlier `GW703`. That is by design: `GW701` is exactly the statement "the
faulty line did not survive to the fix", which is the property this scenario tests. The
blame numbers in the table above were measured on the line the BFC really modifies.

## What a tool must do to pass

- Report exactly `{c1}`. The only evidence that separates `c1` from `c2` is the region named
  in the messages: `c1` bypasses the **EU** challenge (PAY-314) and the BFC requires the
  **EU** challenge again (PAY-501), while `c2` (PAY-330) is about **Canada** and `c3`
  (PAY-352) only restructures the method.
- Not report `c3`, even though line-based blame lands there under every variant.
- Not report `c2`, even though it is one commit closer to the fix, has the same shape, and
  is reached by the same line-history walk.

## Behaviour check (measured)

`CheckoutChallengeGate.requiresChallenge(String, boolean, int)` was run on 91 probes:
regions `{"EU", "CA", "US", "eu", ""}` x `merchantRiskFlag {false, true}` x risk scores
`{MIN_VALUE, MIN_VALUE+1, -1, 0, 69, 70, 71, MAX_VALUE-1, MAX_VALUE}` — the limits of `int`
and the constant `HIGH_RISK_SCORE = 70` with its neighbours — plus one `null`-region probe
(`NullPointerException` in every snapshot, before and after the refactor).

- `c1` (BIC) differs from `c0` on **9** probes: EU with `merchantRiskFlag = false` no longer
  requires the challenge.
- `c2` differs from `c1` on **5** probes, all in the CA region — a real, intended behaviour
  change, not a refactor.
- `c3` is **identical to `c2`** on all 91 probes, i.e. the merge really preserves behaviour.
- `c4` (BFC) differs from `c3` on exactly the **9** EU probes and restores `c0`'s EU
  behaviour; it differs from `c0` on exactly the **5** CA probes, i.e. it keeps `c2`'s
  intended change and undoes nothing else.

All five commit snapshots compile with `javac` (JDK 25): 0 failures out of 5.

## Required graph-schema features

- Factors: context, commit_messages
- Operation types: write_file, replace
- Expected SZZ policy is defined in `expected_szz`.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0098/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0098: Only commit message provides the clue

## Source

- Category: Issue, message, context, and non-local evidence (G7)

## Purpose

Evaluate whether a context-aware SZZ method can use **commit-message** evidence when the
changed code is a generic boolean gate and line-based blame points at a behaviour-preserving
refactor instead of at the commit that disabled the check.

Before this repair, plain blame at `BFC^` already reached the BIC (so the message clue was
not required) and the fault statement `return merchantRiskFlag;` occurred three times in the
file (verifier warning `GW664`); the intermediate commit also tested
`merchantRiskFlag && region.length() == 2`, which is meaningless for a two-letter region
code (issue #4).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          (branch: main, linear)

c0  Add the regional checkout challenge gate
    EU -> return true; CA -> merchantRiskFlag || riskScore >= HIGH_RISK_SCORE; else -> riskScore >= HIGH_RISK_SCORE
c1  PAY-314 bypass the EU checkout challenge while the consent copy rolls out   <- BIC
    EU branch becomes `return merchantRiskFlag;`
c2  PAY-352 collapse the regional gate into a switch                            behaviour-preserving refactor
    the three if-branches become a switch; every branch line is rewritten
c3  PAY-501 require the checkout challenge for EU orders again                  <- BFC
    the EU case becomes `return true;`
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c3`
- `related_but_not_correct`: `c2` — the commit plain blame actually reaches

## Measured plain-blame outcome at BFC^

`BFC^` is `c2`. The BFC deletes exactly one line:

```text
src/main/java/example/CheckoutChallengeGate.java:9  "        return merchantRiskFlag;"  ->  c2
```

Outcome: **miss** (with one extra). `git blame` reaches `c2`, the refactor, and never `c1`.
Generation therefore prints, by design:

```text
[WARNING] GW703: bug B001: basic git blame reaches d74d4eaa..., not expected graph BIC hash(es).
```

`d74d4eaa` is `c2`. `GW664` is gone: the fault statement `return merchantRiskFlag;` occurs
exactly once at `c1` (the CA branch reads `return merchantRiskFlag || riskScore >= HIGH_RISK_SCORE;`,
which does not contain it), and the fix statement `return true;` occurs exactly once at `c3`.

## What a tool must do to pass

- Report exactly `{c1}`. The code alone cannot distinguish `c1` from `c2`: the EU expression
  is textually the same before and after the refactor, and the three regional branches are
  all generic booleans. The only evidence is in the messages: `c1` says it bypasses the EU
  checkout challenge (PAY-314) and the BFC says it requires it again (PAY-501), while `c2`
  (PAY-352) only restructures the method.
- Not report `c2`, even though line-based blame lands there.

## Behaviour check (measured)

`CheckoutChallengeGate.requiresChallenge(String, boolean, int)` was run on 108 inputs:
regions `{"EU", "CA", "US", "eu", "", null}` x `merchantRiskFlag {false, true}` x risk scores
`{MIN_VALUE, MIN_VALUE+1, -1, 0, 69, 70, 71, MAX_VALUE-1, MAX_VALUE}` — the limits of `int`
and the constant `HIGH_RISK_SCORE = 70` written in the source, with its neighbours
(a `null` region throws `NullPointerException` in every snapshot, before and after the
switch refactor).

- `c1` (BIC) differs from `c0` on 9 probes: EU with `merchantRiskFlag = false` no longer
  requires the challenge.
- `c2` is **identical to `c1`** on all 108 probes, i.e. the refactor really preserves
  behaviour.
- `c3` (BFC) is **identical to `c0`** on all 108 probes.

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

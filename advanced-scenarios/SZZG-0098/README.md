# SZZG-0098: Commit message names the regressed region

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `context`, `commit-messages` |
| oracle | `exact_set`; required `c1`; related but not correct `c2`, `c3` · BFC `c4` |
| graph features | `context` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a context-aware SZZ method can use **commit-message** evidence when a
behaviour-preserving refactor has deleted the faulty line *together with an equally shaped
line written by an innocent commit*, so that no line-based blame variant separates the two
candidates.

Two repairs led to the current history:

* the original scenario had plain blame reaching the BIC directly, a meaningless
  `region.length() == 2` test and a thrice-repeated fault statement (issue #4);
* the first repair moved the faulty line into a `switch` **without changing its text**, so
  `git blame -w` recovered `c1` immediately and the message clue was still not required
  (PR #33 review finding 1). The refactor now *deletes* the line instead of re-indenting it;
* the title and the claims were then narrowed, because a blame miss does not establish that
  the code carries no discriminating evidence — see *What the code still reveals* below
  (PR #33 re-review finding 2).

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

- Report exactly `{c1}`. The messages separate `c1` from `c2` directly, by the region they
  name: `c1` bypasses the **EU** challenge (PAY-314) and the BFC requires the **EU**
  challenge again (PAY-501), while `c2` (PAY-330) is about **Canada** and `c3` (PAY-352)
  only restructures the method.
- Not report `c3`, even though line-based blame lands there under every variant.
- Not report `c2`, even though it is one commit closer to the fix, has the same shape, and
  is reached by the same line-history walk.

## What the code still reveals

Message evidence here is **sufficient and direct, not strictly necessary**. Two code-only
routes to `c1` exist and are recorded so that results on this scenario are not over-read.

With messages suppressed, `git show --format= --unified=1` shows the region in the patch
context of each candidate and in the fix itself:

```text
c1  @@ -7,3 +7,3 @@
       if (region.equals("EU")) {
    -    return true;
    +    return merchantRiskFlag;

c2  @@ -10,3 +10,3 @@
       if (region.equals("CA")) {
    -    return true;
    +    return merchantRiskFlag || riskScore >= HIGH_RISK_SCORE;

c4  @@ -7,3 +7,3 @@
       if (region.equals("EU") || region.equals("CA")) {
    -    return merchantRiskFlag || (region.equals("CA") && riskScore >= HIGH_RISK_SCORE);
    +    return region.equals("EU") || merchantRiskFlag || (region.equals("CA") && riskScore >= HIGH_RISK_SCORE);
```

The BFC's added line contains `region.equals("EU")`, so a tool that compares the fix hunk
with the candidate hunks *and their context* can select `c1` without reading a message.
The behaviour of the candidates discriminates as well — with `merchantRiskFlag = false` and
`riskScore = 0` (measured):

| region | c0 | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|
| EU | true | **false** | false | false | **true** |
| CA | true | true | **false** | false | false |

The EU verdict flips at `c1` and back at `c4`; the CA verdict flips at `c2` and stays.

This is a general property of self-contained code repositories: a fix commit names what it
repairs, so a scenario in which message evidence is *strictly* necessary is not constructible
this way. What this scenario establishes is that **every tested blame baseline fails while
message evidence succeeds**, which is the axis the G7 category is about. The same limitation
is recorded for SZZG-0102, where the alternative code route is the call graph.

## Behaviour check (measured)

`CheckoutChallengeGate.requiresChallenge(String, boolean, int)` was run on 235 probes:
regions `{"EU", "CA", "US", "eu", "ca", "", " ", "EU ", " EU", "E U", "\u3000", "EUR", "C"}`
x `merchantRiskFlag {false, true}` x risk scores
`{MIN_VALUE, MIN_VALUE+1, -1, 0, 69, 70, 71, MAX_VALUE-1, MAX_VALUE}` — the limits of `int`
and the constant `HIGH_RISK_SCORE = 70` with its neighbours — plus one `null`-region probe
(`NullPointerException` in every snapshot, before and after the refactor). The region grid
includes case variants, padded and split forms and a full-width space, because `equals` is
exact and a narrow grid would not show it.

- `c1` (BIC) differs from `c0` on **9** probes: EU with `merchantRiskFlag = false` no longer
  requires the challenge.
- `c2` differs from `c1` on **5** probes, all in the CA region — a real, intended behaviour
  change, not a refactor.
- `c3` is **identical to `c2`** on all 235 probes, i.e. the merge really preserves behaviour.
- `c4` (BFC) differs from `c3` on exactly the **9** EU probes and restores `c0`'s EU
  behaviour; it differs from `c0` on exactly the **5** CA probes, i.e. it keeps `c2`'s
  intended change and undoes nothing else.

All five commit snapshots compile with `javac` (JDK 25): 0 failures out of 5.

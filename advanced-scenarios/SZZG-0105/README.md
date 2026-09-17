# SZZG-0105: Defensive check BFC masks an earlier root-cause BIC

## Source

- Category: Issue, message, context, and non-local evidence (G7)

## Purpose

Evaluate whether SZZ finds the commit that introduced the **root cause** when the fix is a
defensive check placed in a **caller that the BIC never touched**. Line-based blame at the
BFC reaches the commit that created the caller, so only reasoning about where the bad value
comes from leads to the real BIC.

Before this repair the BFC edited exactly the line the BIC had written, so `root_cause_not_touched`
was false and plain blame solved the scenario trivially (issue #4).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          (branch: main, linear)

c0  Add the profile name formatter and the profile card
    Profile.displayName -> (first + " " + last).trim()
    ProfileCard.header  -> profile.displayName(first, last).toUpperCase()
c1  Report no display name for profiles whose name parts are blank      <- BIC (root cause)
    displayName now returns null when the trimmed name is empty
c2  Add a sort key derived from the profile name                        (adds Profile.sortKey)
c3  Guard the profile card header against a missing display name        <- BFC (defensive)
    header now does: String name = ...; return name == null ? "" : name.toUpperCase();
```

`Profile.java` (where the root cause lives) is **not** touched by the BFC; `ProfileCard.java`
(where the defensive check lands) is **not** touched by the BIC.

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c3`
- `related_but_not_correct`: `c0` — the commit plain blame actually reaches

## Measured plain-blame outcome at BFC^

`BFC^` is `c2`. The BFC deletes exactly one line:

```text
src/main/java/example/ProfileCard.java:7
  "    return profile.displayName(first, last).toUpperCase();"   ->  c0
```

Outcome: **miss** (with one extra). `git blame` at `BFC^` reaches `c0`, the commit that
created the caller; the required BIC `c1` is never reached. `c0` is a false positive.

Note on the generator's own check: `verify-graph` blames `fault.statement`
(`return full.isEmpty() ? null : full;` in `Profile.java`) rather than the line the BFC
deletes, and that line *is* blamed to `c1`, so the verification prints `GI703` rather than
`GW703`. The scenario-level blame miss is the measurement above.

## What a tool must do to pass

- Report exactly `{c1}`, i.e. follow the `null` that `header` guards against back to
  `Profile.displayName`, and from there to the commit that made the method return `null`.
- Not report `c0` (the caller's author) even though it is the only commit plain blame
  reaches from the fix.

## Behaviour check (measured)

`Profile.displayName(String,String)` and `ProfileCard.header(String,String)` were run on all
64 pairs from `{"", " ", "   ", "\t", "Ada", " Ada ", "Lovelace", null}` (128 probes; the
methods take strings, so the input domain is blank, whitespace-only, padded, ordinary and
`null` name parts rather than integer limits).

- `c1` (BIC) differs from `c0` on 32 probes: 16 `displayName` calls return `null` instead of
  `""`, and the 16 corresponding `header` calls throw `NullPointerException`.
- `c3` (BFC) differs from `c0` on 16 probes, **all of them `displayName`**, and on **zero**
  `header` probes.

That is exactly the contract of a defensive fix, and it is the contract tested here: the
caller's behaviour (`header`) is fully restored to the pre-bug behaviour, while the root
cause (`displayName` returning `null`) is deliberately still present at the BFC — which is
what makes the factor `root_cause_not_touched` true.

## Required graph-schema features

- Factors: defensive_fix, root_cause_not_touched, context_dependent
- Operation types: write_file, replace
- Expected SZZ policy is defined in `expected_szz`.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0105/
|-- scenario.graph.yml
`-- README.md
```

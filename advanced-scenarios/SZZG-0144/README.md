# SZZG-0144: The fix message names the issue whose change blame cannot reach

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `issue-evidence`, `message-evidence`, `tool-visible-context`, `value-flow`, `wrong-constant`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c2`, `c4` · BFC `c6` |
| defeats | `blame`, `shape`, `position` |
| graph features | 2 BICs; 2 fault sites; `issues` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in G7 (issue #35). It is the *value*
kind of the measured axis — a constant's unit changes together with its only
reader, and a later reader assumes the old unit, as in
[SZZ-0190](../../scenarios/SZZ-0190/README.md) and
[SZZG-0117](../SZZG-0117/README.md) — with G7's own evidence on top: three issue
documents committed to the repository and a fix message that names the issue
the unreachable commit closed. A tool that reads only the diff and blame stops
at the consumer; the route to the other half is the issue reference
(`decisions/tool-visible-context.md`).

## Commit structure

```text
c0  Add the session idle policy                                          IDLE_TIMEOUT = 900 (seconds)
c1  Record the request to state the idle timeout in minutes (ISSUE-12)   docs/issues/ISSUE-12.md
c2  Express the idle timeout in minutes (ISSUE-12)                       IDLE_TIMEOUT = 15; expired() compares with IDLE_TIMEOUT * 60   <- BIC
c3  Record the request to show the remaining idle time (ISSUE-19)        docs/issues/ISSUE-19.md
c4  Show the remaining idle time in seconds (ISSUE-19)                   remainingSeconds() = IDLE_TIMEOUT - idleSeconds   <- BIC
c5  Record the report about the negative remaining time (ISSUE-23)       docs/issues/ISSUE-23.md
c6  Compute the remaining idle time from the timeout in minutes, as it has been since ISSUE-12 (ISSUE-23)   IDLE_TIMEOUT * 60 - idleSeconds   <- BFC
```

The history is linear. Every issue document carries a `Reported:` timestamp
that matches `issues[].reported_at` (`GW471`).

## Expected BIC / BFC

- BICs: `c2` and `c4` (`exact_set`, `required: [c2, c4]`)
- BFC: `c6`

Both are necessary. Without `c4` nothing reads `IDLE_TIMEOUT` as seconds;
without `c2` the constant is still 900 and `c4`'s subtraction is right.

## Measured behaviour

`expired(899)`, `expired(900)`, `expired(901)`, `remainingSeconds(20)` and
`remainingSeconds(600)` at each commit (`tests/test_rebalance_scenarios.py`;
`remainingSeconds` exists from `c4`):

| commit | expired(899) | expired(900) | expired(901) | remainingSeconds(20) | remainingSeconds(600) |
|---|---|---|---|---|---|
| `c0`–`c3` | false | false | true | — | — |
| `c4`, `c5` | false | false | true | **-5** | **-585** |
| `c6` | false | false | true | 880 | 300 |

`c2` changes no answer: the constant and its only reader change together.
**Counterfactual, measured:** undoing `c2` on top of `c4` — `IDLE_TIMEOUT = 900`,
`expired()` comparing with it directly, `remainingSeconds()` subtracting from
it directly — gives 880 and 300, the fixed answers, and leaves `expired`
unchanged.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return IDLE_TIMEOUT - idleSeconds;"    plain -> c4    -w -> c4    -w -C -C -> c4
```

Blame returns `{c4}`, half the answer; `c2` is not reachable from the deleted
line by any variant, and the history is linear, so no parent choice helps.

## The evidence a tool can use

- The fix message names two issues. `ISSUE-23` is the report it closes;
  `ISSUE-12` is named as the reason the constant is in minutes. The commit
  that closed `ISSUE-12` is `c2` — its message says so — and of the two commits
  that mention `ISSUE-12`, `c2` is the only one that touches
  `SessionPolicy.java`.
- `docs/issues/ISSUE-23.md` says that sessions still expire after fifteen
  minutes: the constant's meaning agrees with its first reader, so the fault is
  in a *second* reader (`c4`) together with the commit that changed the
  meaning (`c2`).
- The report-date heuristic of [SZZG-0130](../SZZG-0130/README.md) excludes
  nothing here: `c2` and `c4` both predate `ISSUE-23`.

## What a tool must do to pass

Report exactly `{c2, c4}`. `c4` is blame's answer. `c2` has to be reached
either by following `IDLE_TIMEOUT` from the fixed expression to the commit
that changed what it means, or by following the issue reference in the fix
message to the commit that closed `ISSUE-12`. A tool that reports `{c4}`
alone, or `{c4, c1}` because `c1` also mentions `ISSUE-12`, fails.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

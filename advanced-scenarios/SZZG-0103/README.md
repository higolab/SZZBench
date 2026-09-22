# SZZG-0103: Caller-side context is needed to identify the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `context-dependent`, `caller-callee`, `not-directly-local` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ can identify a BIC that lives at a call site when the BFC repairs the observed behaviour
in the callee instead. The BIC and the BFC touch different files, and the line changed by the BFC was written
by the initial commit, not by the BIC.

## Commit history

```text
c0: create AccountService.active and LoginController.canLogin
c1: negate the callee result in LoginController.canLogin (BIC)
c2: invert the condition in AccountService.active so that the double negation restores the original behaviour (BFC)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | `AccountService.active(status)` returns `"ACTIVE".equals(status)`; `LoginController.canLogin(status)` returns `service.active(status)`. |
| `c1` | `main` | `c0` | bug_introducing | `canLogin` becomes `!service.active(status)`: active accounts are rejected, every other status is accepted. |
| `c2` | `main` | `c1` | bug_fixing | `active` becomes `!"ACTIVE".equals(status)`. The caller's negation and the callee's negation cancel out, so `canLogin` behaves as in `c0` again. |

## Code states

Behaviour at each commit (obtained by compiling every generated commit with `javac` and running a small harness):

| Call | `c0` | `c1` (buggy) | `c2` (fixed) |
|---|---|---|---|
| `active("ACTIVE")` | `true` | `true` | `false` |
| `active("DISABLED")` | `false` | `false` | `true` |
| `canLogin("ACTIVE")` | `true` | `false` | `true` |
| `canLogin("DISABLED")` | `false` | `true` | `false` |
| `canLogin(null)` | `false` | `true` | `false` |

`canLogin` is the observable behaviour and is identical at `c0` and `c2`. The fix is a callee-side
compensation of a caller-side bug: after `c2`, `AccountService.active` returns the opposite of what its name
suggests, which is a realistic "fix at the wrong layer" pattern.

## Oracle

- Expected BIC: `c1` (exact set)
- Bug-fixing commit: `c2`
- Fault: `return !service.active(status);` in `LoginController.java` (`c1`)
- Fix: `return !"ACTIVE".equals(status);` in `AccountService.java` (`c2`)

## Expected plain-blame behaviour

The BFC modifies one line of `AccountService.java`. `git blame` at `c2^` (checked on the generated repository):

| Line at `c2^` | Blamed commit |
|---|---|
| `return "ACTIVE".equals(status);` in `AccountService.java` (the line the BFC changes) | `c0` |
| `return !service.active(status);` in `LoginController.java` (the actual fault) | `c1` |

Plain blame on the fixed line reaches `c0`, which is not the BIC. Reaching `c1` requires caller-side context:
the callee `active` is only called from `LoginController.canLogin`, and the change history of that call site
(negated in `c1`) explains why the callee-side inversion fixes the bug. This is a non-trivial G7 case by design.

## Files

```text
SZZG-0103/
|-- scenario.graph.yml
`-- README.md
```

## History

- 2026-09 (issue 1): the BFC previously changed the callee to `return !"DISABLED".equals(status);`, which left
  `canLogin` true only for `DISABLED` accounts, i.e. the "fix" did not fix the bug. It now uses
  `return !"ACTIVE".equals(status);`. Commit messages were rewritten to realistic, role-neutral text. The
  oracle (BIC `c1`, BFC `c2`) is unchanged.

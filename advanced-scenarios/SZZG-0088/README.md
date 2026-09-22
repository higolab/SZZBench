# SZZG-0088: Partial revert of fix reintroduces one fault

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `revert`, `partial-revert`, `reintroduced-bug`, `single-fault-reintroduced`, `re-bic`, `wrong-variable` |
| oracle | default: `exact_set`; required `c3`; related origins `c1`; related but not correct `c2` · `origin-aware`: `relaxed_with_related`; required `c3`; acceptable `c1` (credit 0.5); related but not correct `c2` · BFC `c4` |
| graph features | 2 BICs; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

`Greeting.greet` has two lines that matter: a null guard for the name and the
choice of salutation. `c1` breaks both (drops the guard, swaps "Dear" and
"Hi"); `c2` fixes both; `c3` partially reverts `c2` and swaps the salutations
again while leaving the guard in place; `c4` fixes the salutations. For the
final fix the direct BIC is the partial revert `c3`, not the original `c1`
(origin) and not the prior fix `c2` (`related_but_not_correct`).

Rewritten 2026-09-21 (issue #13) from the shared `aboveMin`/`belowMax` template;
the history shape, oracle and coverage dimensions (`bic_depth` 1, three
distractors on the fault file, 5 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* d41f42b  2024-06-17  Use "Dear" for formal greetings again                           <- BFC (c4)
* 0022d0b  2024-06-11  Revert the salutation change                                    <- BIC (c3; partial revert of c2)
* f1796ef  2024-06-03  Guard the name and use the salutations the right way round      (c2, prior fix; related_but_not_correct)
* e2d4d8e  2024-05-27  Streamline the greeting                                         <- origin (c1; both faults)
* 2b79a48  2024-05-24  Add the greeting helper                                         (c0)
```

## Expected BIC / BFC

- default: `required: [c3]`, `related_but_not_correct: [c2]`, `related_origins: [c1]`
- `origin-aware`: `relaxed_with_related`, `c1` at 0.5
- BFC: `c4`

## Measured behaviour and blame

| commit | `greet("Ada", true)` | `greet("Ada", false)` | `greet(null, true)` |
|---|---|---|---|
| `c0` | `Dear Ada` | `Hi Ada` | `Dear guest` |
| `c1` | **`Hi Ada`** | **`Dear Ada`** | **throws `NullPointerException`** |
| `c2` | `Dear Ada` | `Hi Ada` | `Dear guest` |
| `c3` | **`Hi Ada`** | **`Dear Ada`** | `Hi guest` (guard still fixed) |
| `c4` | `Dear Ada` | `Hi Ada` | `Dear guest` |

`c4` deletes one line (`String prefix = formal ? "Hi " : "Dear ";`, line 6);
blame at `c4^` returns `c3` (verifier `GI703`).

## What a tool must do

Report `c3`. The same faulty text was first written by `c1`, but that instance
was fixed by `c2`; the instance the final fix repairs was written by the partial
revert. A tool that searches history for the first appearance of the faulty text
answers `c1`, which the default oracle rejects.

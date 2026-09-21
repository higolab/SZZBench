# SZZG-0041: Ambiguous blame with duplicate faulty lines

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `ambiguous-blame`, `duplicate-code`, `same-statement-multiple-locations` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ resolves a deleted statement that occurs **twice, byte for byte**, in the BFC parent.

`example.Limits` checks an admin limit and a user limit. Both methods resolve their bound into a local `limit`
variable, so both decide with the same statement, `return value <= limit;`. `c1` makes the user check exclusive
and `c2` makes the admin check exclusive, so from `c2` on the file contains two identical `return value < limit;`
lines whose last change came from two *different* commits. The BFC `c3` repairs only the user check.

Picking the wrong occurrence yields the wrong answer, which is the whole point of the scenario.

## Commit history

```text
c0: add Limits with an inclusive admin check and an inclusive user check
c1: make the user check exclusive (BIC, second occurrence of the statement)
c2: make the admin check exclusive, producing two identical statements (first occurrence)
c3: restore the inclusive user check (BFC, second occurrence)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates `Limits` with `ADMIN_LIMIT = 1000`, `USER_LIMIT = 100`, `withinAdminLimit(int)` and `withinUserLimit(int)`; both end in `return value <= limit;`. |
| `c1` | `main` | `c0` | bug_introducing | `replace ... occurrence: 2` turns the **user** statement into `return value < limit;`. |
| `c2` | `main` | `c1` | other | Turns the **admin** statement into `return value < limit;`. From here the two statements are byte-identical. This change is never undone. |
| `c3` | `main` | `c2` | bug_fixing | `replace ... occurrence: 2` restores `return value <= limit;` in the **user** method only. |

`c1` and `c3` must state `occurrence: 2` because their `old` text matches two lines of the file; without it the
operation is rejected as not unique. That is the schema-level symptom of the ambiguity the scenario models.

## Oracle

- Expected BIC: `c1` (exact set)
- Bug-fixing commit: `c3`
- Fault: `return value < limit;` in `withinUserLimit` (`c1`)
- Fix: `return value <= limit;` in `withinUserLimit` (`c3`)
- `c2` changed the *other* occurrence of the same text in a different method and is **not** a BIC of this bug.

## Measured plain-blame behaviour at `c3^`

`Limits.java` at `c3^`:

```text
 7   public boolean withinAdminLimit(int value) {
 8     final int limit = ADMIN_LIMIT;
 9     return value < limit;        <- written by c2
10   }
11
12   public boolean withinUserLimit(int value) {
13     final int limit = USER_LIMIT;
14     return value < limit;        <- written by c1, deleted by the BFC
15   }
```

`git diff -U0 c3^ c3` is unambiguous about the position: `@@ -14 +14 @@`, one deleted and one added line.
Measured on the generated repository:

| Command | Result | Verdict |
|---|---|---|
| `git blame -L14,14 c3^ -- Limits.java` (the deleted line) | `c1` | **exact** |
| `git blame c3^ -- Limits.java` (whole file), line 14 | `c1` | exact |
| `git blame -w -M -C -L14,14 c3^ -- Limits.java` | `c1` | exact |
| `git log -L14,14:src/main/java/example/Limits.java` | `c1`, then `c0` | exact (`c1` is the most recent) |
| `git blame -L9,9 c3^ -- Limits.java` (the *other* identical line) | `c2` | the wrong-occurrence answer |
| `git log -S'return value < limit;' c3^` | `c2`, `c1` | text search cannot separate the two |

So the plain-blame outcome at `c3^` is **exact** — *provided* the line number from the BFC diff is used. Every
resolution that goes through the statement *text* is ambiguous: the two candidate lines are identical, the admin
one comes first in the file, and it blames `c2`.

The graph verifier reports `GW703` for this scenario. That is the designed effect and is not silenced: the
verifier resolves `fault.statement` by first textual match, lands on line 9 (the admin duplicate) and therefore
reaches `c2` instead of the required `c1`.

## What a tool must do to pass

- Report exactly `{c1}`. `expected_szz.commit_level.evaluation_policy` is `exact_set`.
- Take the deleted line's **position** from the BFC diff instead of re-finding the statement by text. A tool
  that searches for `return value < limit;` in the parent and takes the first hit answers `c2`; a tool that
  takes every hit answers `{c1, c2}`. Both fail the exact set.

## Compilation

All four commit snapshots compile with `javac 25` (`LANG=C`, `-proc:none`, all `.java` files of the snapshot
passed in one invocation): 0 failures.

## Behaviour check

`withinAdminLimit` and `withinUserLimit` were called on every snapshot for 23 values, covering both `int` limits
and the constants written in the source: `Integer.MIN_VALUE`, `Integer.MIN_VALUE + 1`, -1001, -1000, -999, -101,
-100, -99, -1, 0, 1, 2, 50, 99, **100**, 101, 500, 999, **1000**, 1001, 2000, `Integer.MAX_VALUE - 1`,
`Integer.MAX_VALUE` = 46 calls per snapshot. Measured:

| Comparison | Differing calls |
|---|---|
| `c0` -> `c1` (BIC) | exactly 1: `withinUserLimit(100)` `true` -> `false` |
| `c1` -> `c2` | exactly 1: `withinAdminLimit(1000)` `true` -> `false` |
| `c2` -> `c3` (BFC) | exactly 1: `withinUserLimit(100)` `false` -> `true` |
| `withinUserLimit` at `c0` vs `c3` | none: the BFC restores the initial contract on all 23 values |

Contract: the BFC repairs the user check only. `withinAdminLimit(1000)` is `true` at `c0` and `false` from `c2`
on, including at HEAD, because `c2` is a separate change that `c3` deliberately does not undo.

## History

- 2026-09 (issue 4): the two statements the title calls identical were `return value <= 100;` and
  `return value <= 1000;` — different strings, so the `replace` operations were unique, blame was unambiguous
  and the scenario did not realize its factor. Both checks now resolve their bound into a local `limit`, so the
  decisive statement is byte-identical in the two methods, `c1` and `c3` need an explicit `occurrence`, and text
  resolution genuinely picks the wrong line (measured above). The oracle (BIC `c1`, BFC `c3`) and the factors are
  unchanged; the commit messages were rewritten to realistic, role-neutral text.

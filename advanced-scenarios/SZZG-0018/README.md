# SZZG-0018: Only one clone instance is fixed first

## Source

- Category: Clone, copy propagation, and origin-vs-direct BIC (`G2`)

## Purpose

Evaluate two instances of the same fault that are fixed by two *different* commits, so the scenario carries two
bug entries. `A.java` already contains an exclusive range check when the repository is created (`c0`, the origin
instance). `c1` copies that file to `B.java`, so the faulty statement enters `B.java` verbatim; only the class
declaration is adapted so that both classes compile in the same package. `c2` fixes the original instance and
`c3` fixes the copied one.

Both bug-fixing commits are in scope, so the scenario oracle is the union of the two bugs' direct BICs
(contract D9): `c0` wrote the fault into `A.java`, which `c2` fixes, and `c1` copied it into `B.java`, which
`c3` fixes. `c0` is therefore the *direct* BIC of `B001-A` as well as the origin of `B001-B`; because it is
already required, no origin-aware variant is offered — it would be identical to the default.

## Commit history

```text
c0: add A with an exclusive range check (origin instance)
c1: copy A.java to B.java and rename the copied class (direct BIC for B.java)
c2: include the bounds in A.contains (BFC of the original instance)
c3: include the bounds in B.contains (BFC of the copied instance)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | origin_bug_introducing | Creates `example.A` with `contains(int, int, int)` returning `value > min && value < max` (bounds excluded). |
| `c1` | `main` | `c0` | bug_introducing | `copy_file A.java -> B.java`, then one `replace` that turns `public class A {` into `public class B {`. The faulty statement is copied byte-for-byte. |
| `c2` | `main` | `c1` | bug_fixing | BFC of bug `B001-A`: `A.java` gets `return value >= min && value <= max;`. |
| `c3` | `main` | `c2` | bug_fixing | BFC of bug `B001-B`: `B.java` gets the same fix. |

`git show -C -C` on `c1` reports `copy from src/main/java/example/A.java` with `similarity index 87%`: the two
files differ only in the class declaration line.

## Oracle

- Expected BIC (scored set): `c0` and `c1` (exact set)
- Bug `B001-A`: BIC `c0` (role `direct`), BFC `c2`, fault and fix in `A.java`
- Bug `B001-B`: BICs `c1` (role `direct`) and `c0` (role `origin`), BFC `c3`, fault and fix in `B.java`

## Measured plain-blame behaviour at each BFC parent

Each BFC deletes exactly one line (`git diff -U0 <bfc>^ <bfc>`):

| Bug | BFC | Deleted line | `git blame` (plain) | `git blame -C` | `git blame -C -C` (whole file) | `git log -L5,5:<file>` |
|---|---|---|---|---|---|---|
| `B001-B` (scored) | `c3` | `B.java:5` | `c1` | `c1` | `c0`, via `A.java` | `c1` |
| `B001-A` | `c2` | `A.java:5` | `c0` | `c0` | `c0` | `c0` |

For the scored bug `B001-B` the plain-blame outcome at `c3^` is **exact**: plain blame returns `c1`, which is
the required set. `git blame -C -C -L5,5` also returns `c1` (the one-line chunk stays below the copy-detection
score threshold); only whole-file copy detection rewrites the answer to the origin `c0`, which is **not** in
`expected_szz` and would therefore be a miss.

The graph verifier reports `GI703` for `B001-B` and `GW703` for `B001-A`. The `GW703` is expected and
pre-existing: `B001-A` only has a BIC with role `origin`, and the verifier's basic blame check only accepts
`direct`/`reintroducing`/`contributing`. The scenario is not changed to silence it.

## What a tool must do to pass

- Report exactly `{c1}` for the scored bug; plain line-level blame on the line that `c3` deletes already does
  this.
- Keep the two instances apart. The identical statement text is deleted by two different commits; pairing the
  `B.java` fault with the earlier `A.java` fix `c2`, or following the copy into `A.java`, yields `c0` instead.

## Compilation

All four commit snapshots compile with `javac 25` (`LANG=C`, `-proc:none`, all `.java` files of the snapshot
passed in one invocation): 0 failures. `A.java` declares `class A` and `B.java` declares `class B`, both in
package `example`.

## Behaviour check

`contains` was called on every class present in a snapshot for 22 values
(`Integer.MIN_VALUE`, `Integer.MIN_VALUE + 1`, -1000, -11, -10, -6, -5, -4, -1, 0, 1, 4, 5, 6, 7, 9, 10, 11,
100, 1000, `Integer.MAX_VALUE - 1`, `Integer.MAX_VALUE`) crossed with 8 bound pairs (`(5,10)`, `(0,0)`,
`(-1,1)`, `(-10,-5)`, `(10,5)`, `(MIN,MAX)`, `(MIN,MIN+1)`, `(MAX-1,MAX)`) = 176 calls per class.

Contract of this scenario: the fault exists from `c0` on, and `c1` is a *copy*, so it adds a second class with
the same faulty behaviour instead of changing existing behaviour. Measured:

| Comparison | Result |
|---|---|
| `A.contains` at `c0` vs `c1` | identical on all 176 calls |
| `B.contains` at `c1` vs `A.contains` at `c1` | identical on all 176 calls (verbatim copy) |
| `A.contains` at `c1` vs `c2` | differs on 13 of 176 calls, exactly the calls where `value` equals `min` or `max` |
| `A.contains` at `c2` vs `c3` | identical |
| `B.contains` at `c1` vs `c2` | identical (the copy survives the first fix) |
| `B.contains` at `c2` vs `c3` | differs on the same 13 of 176 calls |
| `A.contains` vs `B.contains` at `c3` | identical on all 176 calls (both instances inclusive at HEAD) |

## Difference from SZZG-0016

`SZZG-0016` has the same three-commit prefix but fixes both instances in a single commit, so one BFC deletes two
lines with two different line histories. Here each instance gets its own BFC and its own bug entry.

## Files

```text
SZZG-0018/
|-- scenario.graph.yml
`-- README.md
```

## History

- 2026-09 (issue 10): the copy commit produced a second `public class A` in `B.java`, so `c1`, `c2` and `c3` did
  not compile (`class A is public, should be declared in a file named A.java`). The copy commit now renames the
  copied class to `B`, so all four snapshots compile and both files coexist in package `example`. The copied
  faulty statement, the oracle (two bug entries, direct BIC `c1`, origin `c0`, BFCs `c2` and `c3`) and the
  factors are unchanged; the commit messages were rewritten to realistic, role-neutral text.

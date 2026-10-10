# SZZG-0015: Buggy code copied while original is fixed later

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `boundary-condition` |
| oracle | default: `exact_set`; required `c1`; related origins `c0` · `origin-aware`: `relaxed_with_related`; required `c1`; acceptable `c0` (credit 0.5) · BFC `c2` |
| graph features | operation `copy_file`; 2 BICs; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate a copy-propagated bug whose two instances are fixed in two different commits. `A.java` already contains
an exclusive range check when the repository is created. `c1` copies that file to `B.java`, so the faulty
statement enters `B.java` verbatim; only the class declaration is adapted so that both classes compile in the
same package. `c2` fixes the *copied* instance in `B.java`, and only `c3`, later, fixes the *original* in
`B.java`.

For the `B.java` fix the expected direct BIC is the copy commit `c1`. `c0` is origin context, and the earlier
later `A.java` fix `c3` is not the BFC of the copied instance.

## Commit history

```text
c0: add A with an exclusive range check
c1: copy A.java to B.java and rename the copied class (direct BIC for B.java)
c2: include the bounds in B.contains (BFC)
c3: include the bounds in A.contains, later than the copy
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates `example.A` with `contains(int, int, int)` returning `value > min && value < max` (bounds excluded). |
| `c1` | `main` | `c0` | bug_introducing | `copy_file A.java -> B.java`, then one `replace` that turns `public class A {` into `public class B {`. The faulty statement is copied byte-for-byte. |
| `c2` | `main` | `c1` | bug_fixing | Fixes the copied instance in `B.java`. This is the BFC of the recorded bug. `A.java` is untouched. |
| `c3` | `main` | `c2` | bug_fixing | Fixes the original instance in `A.java`, later than the scored fix. |

`git show -C -C` on `c1` reports `copy from src/main/java/example/A.java` with `similarity index 87%`: the two
files differ only in the class declaration line.

## Oracle

- Expected BIC: `c1` (exact set)
- Origin BIC: `c0` (role `origin`, deliberately not listed in `expected_szz`; see issue #3)
- Bug-fixing commit: `c2` (the later `A.java` fix `c3` is *not* the BFC of this bug)
- Fault: `return value > min && value < max;` in `B.java` (`c1`)
- Fix: `return value >= min && value <= max;` in `B.java` (`c2`)

## Measured plain-blame behaviour at `c2^`

`git diff -U0 c2^ c2` deletes exactly one line, `src/main/java/example/B.java:5`. Measured on the generated
repository:

| Command | Result for the deleted line | Verdict |
|---|---|---|
| `git blame c2^ -- B.java` (plain) | `c1` | **exact** |
| `git blame -L5,5 c2^ -- B.java` | `c1` | exact |
| `git blame -C c2^ -- B.java` | `c1` | exact |
| `git blame -C -C c2^ -- B.java` (whole file) | `c0`, via `src/main/java/example/A.java` | origin instead of the direct BIC |
| `git blame -C -C -C c2^ -- B.java` (whole file) | `c0`, via `src/main/java/example/A.java` | origin instead of the direct BIC |
| `git blame -C -C -L5,5 c2^ -- B.java` | `c1` | the one-line chunk stays below the copy-detection score threshold |
| `git log -L5,5:src/main/java/example/B.java` | `c1` | exact |

The plain-blame outcome at `c2^` is **exact**. The graph verifier confirms this with `GI703`; there is no
designed blame miss in this scenario.

## What a tool must do to pass

- Report exactly `{c1}`. `expected_szz.commit_level.evaluation_policy` is `exact_set`.
- Do not answer with the origin `c0`: whole-file copy detection (`git blame -C -C`) follows the copied block
  into `A.java` and reaches `c0`, which is related history but not the commit that introduced the fault into the
  fixed file.
- Do not pair the `B.java` fault with the later `A.java` fix `c3`. `c3` touches the same statement text in a
  different file and is a plausible but wrong BFC for this bug; a tool that starts from `c2` would blame `c0`.

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
| `A.contains` at `c2` vs `c3` | identical (the original is not touched again) |
| `B.contains` at `c1` vs `c2` | identical (the copy is still faulty after the original is fixed) |
| `B.contains` at `c2` vs `c3` | differs on the same 13 of 176 calls |
| `A.contains` vs `B.contains` at `c3` | identical on all 176 calls (both instances inclusive at HEAD) |

## Difference from SZZG-0014

`SZZG-0014` never fixes the original: `A.java` still excludes the bounds at HEAD. Here `c2` fixes the original
first, which adds a second, wrong candidate BFC for the copied instance.

## History

- 2026-09 (issue 10): `A.java` declared `public class Range`, so *no* commit of this scenario compiled
  (`class Range is public, should be declared in a file named Range.java`), and the copy produced a second
  `public class Range` in `B.java`. The class in `A.java` is now `A`, and the copy commit renames the copied
  class to `B` in the same commit, so every snapshot compiles and both files coexist in package `example`. The
  copied faulty statement, the oracle (`c1` direct, `c0` origin, `c3` BFC) and the factors are unchanged; the
  commit messages were rewritten to realistic, role-neutral text.

## Difference from SZZG-0018

SZZG-0018 fixes the original first and the clone afterwards. This scenario reverses that order, so the
original is the instance that stays faulty longest. Before the 2026-09 repair both scenarios generated
byte-identical repositories (issue #11).

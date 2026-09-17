# SZZG-0016: Original and clone fixed together

## Source

- Category: Clone, copy propagation, and origin-vs-direct BIC (`G2`)

## Purpose

Evaluate a single BFC that repairs two instances of the same fault whose line histories end in two *different*
commits. `A.java` already contains an exclusive range check when the repository is created (`c0`, the origin
instance). `c1` copies that file to `B.java`, so the faulty statement enters `B.java` verbatim; only the class
declaration is adapted so that both classes compile in the same package. `c2` fixes both files in one commit.

The required answer is the copy commit `c1`, the direct BIC of the copied instance. `c0` is the origin: it wrote
the statement that `c2` also deletes from `A.java`, so it is `acceptable_related` with partial credit rather
than a wrong answer.

## Commit history

```text
c0: add A with an exclusive range check (origin instance)
c1: copy A.java to B.java and rename the copied class (direct BIC for B.java)
c2: include the bounds in A.contains and B.contains (BFC for both instances)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | origin_bug_introducing | Creates `example.A` with `contains(int, int, int)` returning `value > min && value < max` (bounds excluded). |
| `c1` | `main` | `c0` | bug_introducing | `copy_file A.java -> B.java`, then one `replace` that turns `public class A {` into `public class B {`. The faulty statement is copied byte-for-byte. |
| `c2` | `main` | `c1` | bug_fixing | One commit, two `replace` operations: both `A.java` and `B.java` get `return value >= min && value <= max;`. |

`git show -C -C` on `c1` reports `copy from src/main/java/example/A.java` with `similarity index 87%`: the two
files differ only in the class declaration line.

## Oracle

- Expected BIC: `c1` (exact set)
- `acceptable_related`: `c0` (`reason: origin_bic`, `credit: 0.5`)
- Bug-fixing commit: `c2`
- Faults: `return value > min && value < max;` in `A.java` (`c0`, role `origin`) and in `B.java` (`c1`, role `direct`)
- Fixes: `return value >= min && value <= max;` in `A.java` and in `B.java`, both in `c2`

## Measured plain-blame behaviour at `c2^`

`git diff -U0 c2^ c2` deletes exactly two lines: `src/main/java/example/A.java:5` and
`src/main/java/example/B.java:5`. Measured on the generated repository:

| Deleted line | `git blame` (plain) | `git blame -C` | `git blame -C -C` (whole file) | `git log -L5,5:<file>` |
|---|---|---|---|---|
| `A.java:5` | `c0` | `c0` | `c0` | `c0` |
| `B.java:5` | `c1` | `c1` | `c0`, via `A.java` | `c1` |

Plain blame over the whole BFC therefore returns `{c0, c1}`: the required `c1` **plus** the origin `c0`. Against
the `exact_set` policy with `required: [c1]` that is an **extra** result — `c0` is not wrong (it carries 0.5
credit as `acceptable_related`), but a tool that stops at the raw blame set does not produce the exact set.

`git blame -C -C` is worse rather than better here: it rewrites the `B.java` answer to `c0` as well, so a
copy-aware tool that only follows copies returns `{c0}` alone, i.e. a **miss** of the required `c1`.

The graph verifier reports `GW703` for this scenario. That is expected and pre-existing: its basic blame check
uses the *first* recorded fault, which is the origin fault in `A.java`, and that line legitimately blames `c0`,
a BIC with role `origin` (the check only accepts `direct`/`reintroducing`/`contributing`). The scenario is not
changed to silence it.

## What a tool must do to pass

- Report exactly `{c1}` for the recorded bug; `c0` is tolerated with partial credit but does not make the set
  exact.
- Separate the two deleted lines instead of scoring the BFC as one blob: the two lines carry the same text but
  different line histories, and only the `B.java` line reaches the required commit.

## Compilation

All three commit snapshots compile with `javac 25` (`LANG=C`, `-proc:none`, all `.java` files of the snapshot
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
| `B.contains` at `c1` vs `c2` | differs on the same 13 of 176 calls |
| `A.contains` vs `B.contains` at `c2` | identical on all 176 calls (both instances inclusive at HEAD) |

## Difference from SZZG-0018

`SZZG-0018` has the same three-commit prefix but fixes the two instances in two separate commits, which splits
the oracle into two bugs. Here a single commit fixes both, so one BFC has two deleted lines with two different
line histories.

## Files

```text
SZZG-0016/
|-- scenario.graph.yml
`-- README.md
```

## History

- 2026-09 (issue 10): the copy commit produced a second `public class A` in `B.java`, so `c1` and `c2` did not
  compile (`class A is public, should be declared in a file named A.java`). The copy commit now renames the
  copied class to `B`, so all three snapshots compile and both files coexist in package `example`. The copied
  faulty statement, the oracle (`c1` direct, `c0` `acceptable_related`, `c2` BFC) and the factors are unchanged;
  the commit messages were rewritten to realistic, role-neutral text.

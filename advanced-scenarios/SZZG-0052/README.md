# SZZG-0052: Criss-cross merge

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `merge`, `criss-cross-merge`, `multiple-merge-bases` |
| oracle | `exact_set`; required `a1` · BFC `c5` |
| graph features | 3 branches; merge commits `a2`, `b2`, `c4` |
<!-- /szzbench:header -->

## Purpose

Two feature branches exchange merges before they are integrated: `a2` merges
`feature-reporting` into `feature-timeout` and `b2` merges `feature-timeout`
into `feature-reporting`. Neither `a1` nor `b1` is then an ancestor of the
other, while both are ancestors of both tips, so the integration merge on
`main` has **two merge bases** and Git has to build a virtual merge base for
it. The bug introduced on `feature-timeout` reaches the bug-fixing commit
through two different merge paths.

The previous version was not a criss-cross: it merged `c2` into `c1` and then
that merge back into `c2`, so `c2` was an ancestor of the other parent and
`git merge-base --all` returned a single base (GitHub issue 4).

## Commit graph (as generated)

`git log --all --graph`, with the logical ids in place of the hashes:

```text
* c5 (HEAD -> main) Accept the timeout range bounds again so 30 s and 3600 s stay valid
*   c4 Merge branch 'feature-reporting' into main
|\
| *   b2 (feature-reporting) Merge branch 'feature-timeout' into feature-reporting
| |\
* | | a3 (feature-timeout) Clamp session timeouts to the accepted range
* | | a2 Merge branch 'feature-reporting' into feature-timeout
|\| |
| |/
|/|
| * b1 Add SessionReporter for timeout diagnostics
* | a1 Require session timeouts strictly inside the accepted range
|/
* c0 Add SessionWindow with the accepted timeout range
```

`a2 = merge(a1, b1)`, `b2 = merge(b1, a1)`, `c4 = merge(a3, b2)`.

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add SessionWindow with the accepted timeout range |
| `a1` | `feature-timeout` | c0 | `bug_introducing` | Require session timeouts strictly inside the accepted range |
| `b1` | `feature-reporting` | c0 | `intermediate` | Add SessionReporter for timeout diagnostics |
| `a2` | `feature-timeout` | a1, b1 | `merge` | Merge branch 'feature-reporting' into feature-timeout |
| `b2` | `feature-reporting` | b1, a1 | `merge` | Merge branch 'feature-timeout' into feature-reporting |
| `a3` | `feature-timeout` | a2 | `intermediate` | Clamp session timeouts to the accepted range |
| `c4` | `main` | a3, b2 | `merge` | Merge branch 'feature-reporting' into main |
| `c5` | `main` | c4 | `bug_fixing` | Accept the timeout range bounds again so 30 s and 3600 s stay valid |

Refs after generation (`git for-each-ref`): `refs/heads/main` → `c5`,
`refs/heads/feature-timeout` → `a3`, `refs/heads/feature-reporting` → `b2`.

### The criss-cross, measured

`git rev-list --parents -n 1 <c4>` prints `c4 a3 b2`, and

```console
$ git merge-base --all <a3> <b2>
9ba44929…   (b1)
799bb89b…   (a1)
```

returns **two** commits, which is the definition of a criss-cross merge. All
merges are conflict-free: the two branches touch disjoint files
(`SessionWindow.java` and `SessionReporter.java`).

Only `feature-timeout` commits again after the exchange (`a3`). That keeps
every merge inside what `validate-graph --simulate` can model — its in-memory
merge resolves against a single nearest common ancestor — while the two merge
bases of `c4` are unaffected.

## Expected SZZ result

```text
Expected BFC: c5
Required BIC: a1
```

## Plain blame outcome (measured)

`git diff -U0 c5^ c5` deletes exactly one line,
`    return seconds > MIN_TIMEOUT_SECONDS && seconds < MAX_TIMEOUT_SECONDS;`
(line 8 of `src/main/java/example/SessionWindow.java`). `git blame` at `c5^`
— which is the criss-cross merge `c4` — returns **`a1`**, the required BIC, so
the outcome is **hit**; `-M`, `-C -C` and `-w` return `a1` as well. Generation
reports `GI703`.

## What a tool must do to pass

Report exactly `{a1}`. `git blame` resolves the criss-cross itself, so the
scenario is a control test for blame-based tools; it discriminates tools that
implement their own history walk. Reporting one of the merge commits `a2`,
`b2` or `c4` (a tool that stops at a merge, or that attributes the line to the
merge that carried it into the fixed branch) is a false positive — they are in
no `expected_szz` list, so they count as hard false positives under
`exact_set`. A walk that picks only one of the two merge bases must still end
at `a1`: the path through `b2` also leads there, because `b2` merged `a1`.

## Behaviour check (measured)

All eight commit snapshots compile with `javac` (JDK 25): 0 failures out of 8.

`SessionWindow.acceptsTimeout(int)`, `SessionWindow.clampTimeout(int)` (from
`a3` on) and `SessionReporter.describeTimeout(int)` (from `b1` on) were probed
over `{Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 29, 30, 31, 3599, 3600, 3601,
MAX_VALUE-1, MAX_VALUE}` (13 inputs: both `int` limits and both boundary
constants, ±1).

* `a1` (BIC) differs from `c0` on **2 of 13** shared probes:
  `acceptsTimeout(30)` and `acceptsTimeout(3600)`.
* `c4` (the criss-cross merge, i.e. `c5^`) still shows the same two
  differences, so the fault survives both merges.
* `c5` (BFC) agrees with `c0` on **all 13** shared probes; its 26 extra probes
  (`clampTimeout`, `describeTimeout`) have no counterpart at `c0`.

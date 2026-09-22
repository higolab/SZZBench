# SZZG-0110: Empty intermediate commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `boundary-condition` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ identifies the real BIC when an **empty** commit sits between the
bug-introducing and the bug-fixing commit. The empty commit is the direct parent of the
BFC, so a tool that walks back from the BFC meets it first and must skip it.

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          (branch: main, linear)

c0  Add the range containment helper                              (creates Range.java, inclusive bounds)
c1  Align contains() with the exclusive interval used by the ...  BIC: >= / <= becomes > / <
c2  Retrigger the release build after the CI cache was cleared    empty commit (no diff at all)
c3  Restore the inclusive bounds of Range.contains()              BFC
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c3`

## Measured plain-blame outcome at BFC^

`BFC^` is the empty commit `c2`. The BFC deletes exactly one line:

```text
src/main/java/example/Range.java:5  "    return value > min && value < max;"  ->  c1
```

Outcome: **exact**. `git blame` at `BFC^` reaches `c1`, which is the required BIC, and no
other commit is reached. The generator's verification reports `GI703` (basic blame reaches
an expected graph BIC).

## What a tool must do to pass

- Report exactly `{c1}`.
- Not report `c2`: it is empty (`git show --stat` prints no file at all), so it changes no
  line and can carry no blame. Tools that take "the commit before the BFC" as a candidate,
  or that fail on a commit whose diff is empty, fail here.

## Structural evidence (measured on the generated repository)

```text
f450ec3 Restore the inclusive bounds of Range.contains()          <- BFC (c3)
5739e9a Retrigger the release build after the CI cache was cleared <- empty, BETWEEN BIC and BFC (c2)
2235a70 Align contains() with the exclusive interval used by ...   <- BIC (c1)
7c7e846 Add the range containment helper                           (c0)
```

`git show --stat 5739e9a` lists no files; `git diff-tree -r c1 c2` is empty.

## Behaviour check (measured)

`Range.contains(int,int,int)` was run on 96 inputs: values
`{MIN_VALUE, MIN_VALUE+1, -6, -5, -4, -1, 0, 1, 6, 7, 8, 9, 10, 11, MAX_VALUE-1, MAX_VALUE}`
against the intervals `(0,10)`, `(-5,5)`, `(7,7)`, `(MIN_VALUE,MAX_VALUE)`, `(MIN_VALUE,0)`,
`(0,MAX_VALUE)`. The BIC `c1` differs from `c0` on the 10 boundary inputs; the BFC `c3`
agrees with `c0` on all 96.

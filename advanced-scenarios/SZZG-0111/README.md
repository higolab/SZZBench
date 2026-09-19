# SZZG-0111: Chmod-only intermediate

## Source

- Category: Non-source, binary, generated, and scalability edge cases (G8)

## Purpose

Evaluate whether SZZ identifies the real BIC when a **mode-only** commit sits between the
bug-introducing and the bug-fixing commit. The commit is a real, non-empty commit whose
diff contains no content line at all, only a file-mode change.

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          (branch: main, linear)

c0  Add the range containment helper and the build script          (scripts/run.sh + Range.java)
c1  Align contains() with the exclusive interval used by the ...   BIC: >= / <= becomes > / <
c2  Mark scripts/run.sh executable so CI can call it directly      chmod 100644 -> 100755, no content change
c3  Restore the inclusive bounds of Range.contains()               BFC
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c3`

## Measured plain-blame outcome at BFC^

`BFC^` is the chmod commit `c2`. The BFC deletes exactly one line:

```text
src/main/java/example/Range.java:5  "    return value > min && value < max;"  ->  c1
```

Outcome: **exact**. `git blame` at `BFC^` reaches `c1`, the required BIC, and nothing else.
The generator's verification reports `GI703`.

## What a tool must do to pass

- Report exactly `{c1}`.
- Not report `c2`. `c2` changes no line, so it can carry no blame, but unlike an empty
  commit it *does* appear in `git log --name-only` and in `git diff-tree --name-status`
  as a modified file (`M scripts/run.sh`). A tool that treats "the file was touched" as
  "a line was changed", or that crashes on a diff without hunks, fails here.

## Structural evidence (measured on the generated repository)

The repository is generated with `core.filemode=true` (the generator enables it
automatically for scenarios that use `chmod`), so the mode change is really recorded:

```text
$ git show --stat --summary c2
 scripts/run.sh | 0
 1 file changed, 0 insertions(+), 0 deletions(-)
 mode change 100644 => 100755 scripts/run.sh

$ git show c2
diff --git a/scripts/run.sh b/scripts/run.sh
old mode 100644
new mode 100755

$ git ls-tree c1 scripts/run.sh   ->  100644 blob df13bcd...
$ git ls-tree c2 scripts/run.sh   ->  100755 blob df13bcd...   (same blob)
$ git diff-tree -r --name-status c1 c2   ->  M  scripts/run.sh   (the commit is not empty)
```

Note: plain `git show --stat` prints only ` scripts/run.sh | 0`; the `mode change` line
comes from `--summary` (which `git show` adds by default for a full diff as
`old mode`/`new mode`).

`scripts/run.sh` is a real build script (`javac -d build/classes src/main/java/example/Range.java`)
and was executed from a checkout of HEAD: it produces `build/classes/example/Range.class`.
The previous `python -m example.Range` nonsense for a Java project is gone.

`c2` keeps `allow_empty: true`, but no longer *needs* it in a normal generation run. It is
kept for the two environments in which the mode change cannot be recorded: the in-memory
simulator behind `validate-graph --simulate`, which still models `chmod` as a no-op (and
would otherwise report `GE202`), and file systems without an executable bit.

## Behaviour check (measured)

`Range.contains(int,int,int)` was run on 96 inputs: values
`{MIN_VALUE, MIN_VALUE+1, -6, -5, -4, -1, 0, 1, 6, 7, 8, 9, 10, 11, MAX_VALUE-1, MAX_VALUE}`
against the intervals `(0,10)`, `(-5,5)`, `(7,7)`, `(MIN_VALUE,MAX_VALUE)`, `(MIN_VALUE,0)`,
`(0,MAX_VALUE)`. The BIC `c1` differs from `c0` on the 10 boundary inputs; the BFC `c3`
agrees with `c0` on all 96.

## Required graph-schema features

- Factors: chmod
- Operation types: write_file, chmod, replace
- Expected SZZ policy is defined in `expected_szz`.

---

## Files

```text
SZZG-0111/
|-- scenario.graph.yml
`-- README.md
```

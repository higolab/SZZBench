# SZZG-0083: Huge noisy rebased commit

## Purpose

Evaluate how a tool behaves when the bug-introducing commit is **genuinely
large**: one faulty source line inside a commit that also regenerates a
machine-written table of about 7000 lines.

## Commit graph

```text
        feature
          |
c0 ────── f1                  f1: the original large commit
 │
 └─────── r1 ── c2   main     r1 = replay of f1, c2 = the fix
```

`git rev-list --parents`: `c2 <- r1 <- c0` on `main`; `f1 <- c0` on `feature`.

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature -> f1 (ac9855c)
refs/heads/main    -> c2 (0e6a1af)
```

## Commit table

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Regenerate the status code table and use strict interval bounds |
| `r1` | `main` | c0 | `bug_introducing` | *(inherited from f1)* Regenerate the status code table and use strict interval bounds |
| `c2` | `main` | r1 | `bug_fixing` | Restore the inclusive comparison in Range.contains |

## Measured size of the noisy commit

`git show --stat r1`:

```text
 src/main/java/example/Range.java            |    2 +-
 src/main/java/example/StatusCodes.java      | 5007 +++++++++++++++++++++++++++
 src/main/resources/status-labels.properties | 2000 +++++++++++
 3 files changed, 7008 insertions(+), 1 deletion(-)
```

`git show --format= r1 | wc -l` = **7031 lines**, `| wc -c` = **289 502 bytes**.
`StatusCodes.java` is a real, compilable Java class (package header, private
constructor, 5000 `public static final int CODE_n = n;` fields, closing brace)
written with `write_generated_text_file` and its `header` / `footer`;
`status-labels.properties` holds 2000 generated entries.

The previous version of this scenario added ten one-line `docs/noise-N.md`
files, which is not a large commit by any measure.

## What the size actually burdens

The fix `c2` deletes exactly **one** line and that line is in `Range.java`:

```text
 src/main/java/example/Range.java | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

so the generated files **never enter deleted-line blame**. Line-level SZZ is
completely unaffected by the 7000 lines.

The commit size burdens

* tools that read or parse **whole patches** — diff parsers, commit
  classifiers, "is this commit a bug fix / how large is it" heuristics, and in
  particular LLM-based tools that put `git show` output into a prompt: 283 KB
  for one commit;
* tools that **scan the repository or the tree at each commit** (checkout per
  commit, static analysis per revision, file-level indexing);
* commit-size features in SZZ variants that weight or filter candidate commits
  by the number of changed files/lines.

This scenario is therefore a control test for line-level blame and a real
stress test for the two classes of tools above.

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Measured blame at `c2^`

`c2` deletes exactly one line:

```text
-    return value > min && value < max;
```

`git blame <c2^> -- src/main/java/example/Range.java` attributes that line to
**`r1`** (`8117a353…`); `git blame -w` gives the same answer. The generator's
verifier reports `GI703`.

## Measured behaviour

Snapshots `c0` (initial), `r1` (BIC) and `c2` (BFC) were compiled with
`javac 25` and `Range.contains(int, int, int)` was executed over the full grid
of all 9³ = 729 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

* `c0` vs `r1`: **81 of 729 inputs differ**.
* `c0` vs `c2`: **identical on all 729 inputs**.

`StatusCodes` declares only constants and no methods, so the reflective driver
has nothing to call there; its values `CODE_1 = 1 … CODE_5000 = 5000` are
checked by `javac`. All 4 commit snapshots compile with `javac` without errors,
including the 5007-line generated class.

## What a tool must do to pass

1. Return exactly `{r1}`.
2. Stay within its time and memory limits on a commit whose patch is 7031
   lines / 283 KB.
3. Not be distracted by the generated files: they are added, never modified,
   and the fix does not touch them.

## Notes

- `large_noisy_rebased_commit: true` records the intent; `rebase_of` records
  the replay relation and `inherit_message` / `inherit_author_date` keep `f1`'s
  subject and author date.
- `validate-graph --simulate` ignores `header` / `footer` of
  `write_generated_text_file`; no operation of this scenario targets header
  text, so simulation and generation agree on every `replace`.

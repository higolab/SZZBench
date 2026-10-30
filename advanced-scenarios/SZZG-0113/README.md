# SZZG-0113: Huge file

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `generated-file` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | operation `write_generated_text_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ survives, and stays precise on, a **one-line fix inside a generated
Java file of more than 10,000 lines**. The huge file exists before the bug-introducing
commit and the bug lives inside it, so blame for the fix really has to run over the whole
file.

Before this repair the huge file was written by the BFC itself (so it never entered blame)
and it was not valid Java: 10,000 top-level field declarations with no class, which `javac`
rejects (issues #4 and #10).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          (branch: main, linear)

c0  Add the generated bounds table and the tier policy
    src/main/java/example/LargeRange.java: 10,005 lines, 437 KiB
      package example; /** Generated bounds table ... */ public class LargeRange {
        public static final int VALUE_1 = 1;  ...  public static final int VALUE_10000 = 10000;
      }
    src/main/java/example/TierPolicy.java reads four of the entries
c1  Regenerate the bounds table after the tier import        <- BIC
    VALUE_5000 becomes 500
c2  Add the script that regenerates the bounds table         tools/generate-bounds.sh
c3  Correct the bound of tier 5000 in the generated table    <- BFC
```

The class is produced by `write_generated_text_file` with the `header`/`footer` options, so
it is a real class. The entries are `static final int` compile-time constants, which keeps
the class initializer empty — 10,000 *instance* field initializers would exceed the 64 KiB
method limit.

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c3`

## Measured plain-blame outcome at BFC^

`BFC^` is `c2`. The BFC deletes exactly one line, line 5004 of a 10,005-line file:

```text
src/main/java/example/LargeRange.java:5004
  "  public static final int VALUE_5000 = 500;"  ->  c1
```

Outcome: **exact** (`GI703`). Both the fault line and the fix line are unique in the file
(`VALUE_5000 = 500;` / `VALUE_5000 = 5000;` occur once), so there is no `GW664`.

## What a tool must do to pass

- Report exactly `{c1}`.
- Do so without truncating or skipping the file: the changed line sits in the middle of a
  437 KiB source file, and tools that cap the file size, the diff size or the blame depth
  will either miss it or fall back to the file's creating commit `c0`.

## Structural evidence (measured on the generated repository)

```text
$ git show HEAD:src/main/java/example/LargeRange.java | wc -lc
   10005   447886          (10,005 lines, 437 KiB)
$ javac src/main/java/example/*.java      -> OK at c0, c1, c2 and c3
```

`tools/generate-bounds.sh` (added by `c2`) really regenerates the file: running it in a
checkout of HEAD produces a file byte-identical to the committed one.

## Behaviour check (measured)

10,015 probes per snapshot: `TierPolicy.upperBound(int)` on
`{MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 2, 500, 4999, 5000, 5001, 9999, 10000, 10001, MAX_VALUE-1, MAX_VALUE}`
(both `int` limits and the four tier constants written in `TierPolicy`), plus every one of
the 10,000 public constants of `LargeRange` read reflectively and compared with its index.

- `c0`: `upperBound(5000) = 5000`; constants sum `50005000`, 0 mismatches.
- `c1` (BIC): `upperBound(5000) = 500`; constants sum `50000500`, exactly 1 mismatch
  (`VALUE_5000 = 500`).
- `c3` (BFC): **identical to `c0`** on all 10,015 probes.

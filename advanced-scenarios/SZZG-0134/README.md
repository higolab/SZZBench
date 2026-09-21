# SZZG-0134: A .gitattributes line-ending rule is the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `gitattributes-bic`, `line-ending`, `non-source-bic`, `cross-artifact-fix` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

[SZZ-0108](../../scenarios/SZZ-0108/README.md) has a CRLF rewrite as an
intermediate commit; [SZZ-0171](../../scenarios/SZZ-0171/README.md) and
[SZZ-0172](../../scenarios/SZZ-0172/README.md) have a dependency and a property
as the BIC. Here the BIC is a repository attribute. The mode list is read from a
text resource and compared line by line; a commit adds `*.txt text eol=crlf` to
`.gitattributes`, so every checkout of the resource ends its lines in `\r\n`,
every line the reader compares carries a trailing `\r`, and no mode matches.
The fix makes the reader tolerate either ending. The faulty change touched no
Java.

## Commit structure (generated)

```text
* 12fa710  Accept Windows line endings when reading the mode list                       <- BFC (c2)  ModeList.java
* 50e87cc  Check text files out with Windows line endings for the packaging tool        <- BIC (c1)  .gitattributes
* 1d7867e  Add the mode list and its reader                                              (c0)
```

**`c1` changes exactly one file, `.gitattributes`** (`git show --stat`). The
scenario also rewrote `modes.txt` with CRLF in that commit, but git normalised it
back to LF on `git add` because the new attribute marks it `text`, so the blob
is byte-identical to `c0`'s and does not appear in the diff. The conversion
happens on the way out: `git archive` of `c1` (which honours attributes) yields
`strict\r\nlenient\r\n…`, while the same archive of `c0` yields `strict\nlenient\n…`.
That is the whole mechanism: the bytes the program reads changed although no
tracked content did.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`); fault statement `*.txt text eol=crlf` in `.gitattributes`
- BFC: `c2`

## Measured behaviour and blame

`contains("strict")` on the checked-out snapshots: `true` at `c0`, **`false`**
at `c1`, `true` at `c2` (`tests/test_twins_and_transitions.py`, on
`git archive` output). Blaming the fault statement's line in `.gitattributes` at
`c2^` returns `c1` (`GI703`). Blaming the line the fix deletes in
`ModeList.java` returns `c0`.

## What a tool must do

Report `c1`. The fix's deleted line was written by `c0`, and `c1` touched no
file the fix touched; the link is that `c1` changed how the resource the fixed
line reads is checked out.

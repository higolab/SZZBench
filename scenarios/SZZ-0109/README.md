# SZZ-0109: Comment-only intermediate before fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `robustness`, `comment-noise` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks that a comment-only commit between the BIC and the BFC
does not disturb bug-introducing-commit identification. The intermediate
commit adds a three-line Javadoc block above the faulty method and changes no
code; the comment is still there after the fix.

It is an honest **control**: plain `git blame` solves it. Its value is that the
comment survives the BFC, so a tool is not rewarded for the accident that the
fix happened to delete the comment along with the faulty line.

## Commit structure

- `c0`: Adds `com.example.quota.QuotaGuard` with `withinQuota(int)`
  (`return used <= maxRequests;`) and `remaining(int)`.
- `c1`: Changes the bound to `return used < maxRequests;`. This is the **BIC**:
  the caller is refused while `remaining()` still reports one request left.
- `c2`: Inserts a Javadoc block above the signature of `withinQuota`. Its diff
  is `+3 -0`; no code line is added, removed or re-indented.
- `c3`: Restores `used <= maxRequests`. This is the **BFC**; its first-parent
  diff is `+1 -1` and the Javadoc block stays in the file.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return used < maxRequests;` (line 14). `git blame` and `git blame -w`
at `c3^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Blame the deleted line and stop. A tool fails by adding `c2` because it is the
most recent commit on the file, or because a hunk-level change model widens
the fix hunk to the comment that immediately precedes the method.

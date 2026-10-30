# SZZ-0199: The unit of a configuration value changes, and a later reader shows it raw

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `non-source-file`, `configuration-change`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. The
unreachable commit is in a **properties file** — where
[SZZ-0194](../SZZ-0194/README.md) puts the other commit in a Java file the fix
never opens, this one puts it outside the language entirely, so a tool that
reasons only over source cannot see it at all.

It is the first scenario in the non-source category (S8) with a two-commit
oracle; the other four are solved by a naive baseline.

## Commit structure

```text
c0  Add the upload limit and its setting       limits.properties = 2048 (KB); maxKilobytes() parses it
c1  State the upload limit in bytes            properties = 2097152; maxKilobytes() divides by 1024   <- BIC
c2  Say where the upload limit is enforced     one more comment line in the properties file (distractor)
c3  Show the upload limit on the upload form   new class: setting("upload.max") + " KB"               <- BIC
c4  Show the upload limit in the unit the label claims   maxKilobytes() + " KB"                       <- BFC
```

`c1` restates the setting in bytes and updates the one reader that interprets
it, so `maxKilobytes()` still answers 2048. `c3` adds a screen that reads the
raw setting and labels it as kilobytes, so the form advertises a limit a
thousand times too large.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

## Measured behaviour (from the generated repository)

```text
c0  Add the upload limit and its setting       maxKilobytes()=2048  setting=2048
c1  State the upload limit in bytes            maxKilobytes()=2048 (unchanged)  setting=2097152
c2  Say where the upload limit is enforced     0 change
c3  Show the upload limit on the upload form   limitLabel()="2097152 KB"   <- the bug
c4  Show the upload limit in the unit the label claims   limitLabel()="2048 KB"
```

The interpreted value never moves; only the raw setting does, which is why no
existing reader notices `c1`.

**Both commits are necessary, measured rather than argued.** `c2` rewrites the
properties file, so `git revert` of `c1` conflicts; undoing `c1`'s two changes
by hand on top of `c3` — the value and the division, keeping `c2`'s comment —
gives the fixed answer:

```text
c3 as shipped                limitLabel() = "2097152 KB"   <- the bug
c3 with c1's change undone   limitLabel() = "2048 KB"
c4 (the fix)                 limitLabel() = "2048 KB"
```

## Measured blame outcome at BFC^

The fix deletes exactly one line, and opens only `UploadForm.java`:

```text
"return UploadLimit.setting(\"upload.max\") + \" KB\";"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}` — half the answer. `c1` is not reachable from the deleted
line by any blame variant, and the file it changed is never opened by the fix.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching `c1` means following the setting key from
the fixed line into a non-source file and finding the commit that changed what
the value means — a step that needs the configuration file to be part of the
history a tool searches at all.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

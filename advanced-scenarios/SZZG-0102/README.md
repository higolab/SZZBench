# SZZG-0102: Issue text names the regressed column

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `issue-evidence`, `context` |
| oracle | `exact_set`; required `c1`; related but not correct `c2`, `c3` · BFC `c4` |
| graph features | `issues`; `context` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ can use the **text behind the issue identifiers** to choose between two
commits that made the same change to two duplicated normalizers, after a deduplication
deleted both changed lines. The commit subjects carry issue identifiers and no column names,
so neither the code nor the subjects say which column regressed.

Two repairs led to the current history:

* the original scenario carried no `ISSUE-482` in any commit message, so a Git-only tool
  could not even find the issue, and plain blame reached the BIC directly (issue #4);
* the first repair moved the faulty line into a nested class **without changing its text**,
  so `git blame -w` recovered `c1` immediately and no context was required (PR #33 review
  finding 1). The refactor now *deletes* the line instead of re-indenting it, and a second
  commit makes the same change to a second column so that the choice is genuinely ambiguous;
* that second commit was first spelled with `value.isBlank()`, which is **not** equivalent to
  a trim-based blank test, so the deduplication silently changed the nickname contract
  (PR #33 re-review finding 1). See *Why the three spellings are equivalent* below.

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the CSV contact importer
    two duplicated normalizers, normalizeMiddleName and normalizeNickname,
    both `value == null ? "" : value.trim()`
c1  ISSUE-401 follow the optional-column contract from the importer API docs      <- BIC
    normalizeMiddleName returns null for blank values
c2  ISSUE-377 apply the same optional-column contract to the profile fields
    normalizeNickname returns null for blank values, spelled `value.trim().length() == 0`
    -> the rival candidate: same change, same behaviour, one commit closer to the fix
c3  ISSUE-510 share one optional-column normalizer between the importer fields
    behaviour-preserving deduplication; the patch deletes the line c1 wrote and the line
    c2 wrote and replaces them with one body whose text matches neither
c4  ISSUE-482 keep blank middle names as empty strings                            <- BFC
    middleName maps a null result back to the empty string; nickname keeps c2's contract
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c4`
- `related_but_not_correct`: `c2` (the equally shaped nickname change) and `c3` (the commit
  blame actually reaches)

## Measured blame outcome at BFC^

`BFC^` is `c3`. The BFC modifies exactly one line, line 5 of
`src/main/java/example/CsvContactImporter.java`:

```text
"    return normalizeOptional(row[1]);"
```

Blame of that line at `c3`, measured in the generated repository:

| variant | result |
|---|---|
| `git blame` | `c3` |
| `git blame -w` | `c3` |
| `git blame -w -M` | `c3` |
| `git blame -w -C -C` | `c3` |

Outcome: **miss** under every variant.

One hop further back does not disambiguate either. The lines `c3` deletes blame, at `c3^`, to

```text
CsvContactImporter.java:13   return value == null || value.trim().isEmpty() ? null : value.trim();  -> c1
CsvContactImporter.java:17   return value == null || value.isBlank() ? null : value.trim();         -> c2
```

(the remaining deleted lines — the two call sites and the two method headers — belong to
`c0`), so the candidate set that line history yields is `{c1, c2}`. Both commits gave the
same null-for-blank contract to an optional column.

Because the fault statement is no longer present at `BFC^`, generation reports

```text
[WARNING] GW701: bug B001: fault.statement not present in final BFC parent; basic blame unavailable.
```

instead of the earlier `GW703`. That is by design: `GW701` states that the faulty line did
not survive to the fix, which is the property this scenario tests. The blame numbers above
were measured on the line the BFC really modifies.

## What a tool must do to pass

- Read `ISSUE-482` from the BFC message — `git log` alone suffices to find the identifier —
  and use its **text**: it names the `middle_name` column and says that the same contract was
  applied to the nickname column on purpose.
- Match that text against the texts of `ISSUE-401` (middle_name) and `ISSUE-377` (nickname).
  The subjects carry the identifiers only; the identifiers themselves are not ordered or
  otherwise informative (`ISSUE-401` is the BIC, `ISSUE-377` is not, although 377 < 401), and
  the two commits are indistinguishable by line-based blame.
- Report exactly `{c1}`, and not `c3`, which every blame variant reaches, nor `c2`.

The four issue texts (`ISSUE-482`, `ISSUE-401`, `ISSUE-377`, `ISSUE-510`) are scenario
metadata under the top-level `issues:` key; the generated repository carries only the
identifiers in the commit subjects. A tool handed the repository alone therefore cannot read
the texts this section relies on — an adapter has to supply them from the YAML. The
tool-visible-context decision ([`docs/decisions/tool-visible-context.md`](../../docs/decisions/tool-visible-context.md),
issue #23) now commits such reports into the repository as `docs/issues/<ISSUE-ID>.md`
documents (SZZG-0130, SZZG-0131 and SZZG-0135–SZZG-0137); this scenario's reports have **not**
been materialized that way, so its issue evidence stays adapter-supplied.

## What the code still reveals

Issue-text evidence here is **sufficient and direct, not strictly necessary**. A tool that
reconstructs the call graph across `c3` can also reach `c1`, because `middleName` called
`normalizeMiddleName` before the deduplication and the BFC repairs the `middleName` path.
What this scenario establishes is that **every tested blame baseline fails while the issue
texts succeed**, not that the code is free of clues. The same limitation, with the patch
context as the alternative code route, is recorded for SZZG-0098.

## Why the three spellings are equivalent

The scenario needs `c1` and `c2` to be textually distinguishable but behaviourally identical,
and `c3` to be a third spelling that preserves both. The three predicates are

```text
c1  value == null || value.trim().isEmpty()      ? null : value.trim()
c2  value == null || value.trim().length() == 0  ? null : value.trim()
c3  String trimmed = value == null ? "" : value.trim(); trimmed.isEmpty() ? null : trimmed
```

`isEmpty()` and `length() == 0` are the same test, and `c3` simply names the trimmed value,
so all three agree on every input. `String.isBlank()` — used in the first version of `c2` —
does **not** agree with them, because `trim()` removes every character up to `U+0020` while
`isBlank()` uses `Character.isWhitespace`:

| input | `isBlank()` | `trim().isEmpty()` | `trim().length() == 0` |
|---|---|---|---|
| `U+0000` (NUL) | false | **true** | **true** |
| `U+2003` (em space) | **true** | false | false |
| `U+3000` (ideographic space) | **true** | false | false |
| `U+00A0` (no-break space) | false | false | false |

The Java probe grid below therefore includes Unicode whitespace; an ASCII-only grid did not
show the regression.

## Behaviour check (measured)

`middleName(String[])` and `nickname(String[])` were run on 24 values — 48 probes per
snapshot:

```text
null, "", " ", "  ", TAB, LF, CR, FF, U+000B,
U+0000, U+0001, U+001F, U+00A0, U+2003, U+2007, U+200B, U+3000,
"x", " x ", "Ann", "  Ann  ", U+3000 + "Ann" + U+3000, NUL + "Ann" + NUL, "A n n"
```

Twelve of them (`null` and the eleven values that `trim()` empties, i.e. every character up
to `U+0020`) are blank under the trim-based contract; `U+00A0`, `U+2003`, `U+2007`, `U+200B`
and `U+3000` are not, and pass through unchanged in every snapshot.

- `c1` (BIC) differs from `c0` on **12** probes: the blank or `null` middle names now come
  back as `null` instead of `""`.
- `c2` differs from `c1` on **12** probes, all of them nicknames — a real, intended behaviour
  change written in a different but equivalent form.
- `c3` is **identical to `c2`** on all 48 probes, i.e. the deduplication really preserves
  behaviour, although its body is textually a third variant.
- `c4` (BFC) differs from `c3` on exactly the **12** middle-name probes and restores `c0`'s
  middle-name contract; it differs from `c0` on exactly the **12** nickname probes, i.e. it
  keeps `c2`'s intended change and undoes nothing else.

All five commit snapshots compile with `javac` (JDK 25): 0 failures out of 5.

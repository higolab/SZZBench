# SZZG-0102: Issue description required

## Source

- Category: Issue, message, context, and non-local evidence (G7)

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
  commit makes the same change to a second column so that the choice is genuinely ambiguous.

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the CSV contact importer
    two duplicated normalizers, normalizeMiddleName and normalizeNickname,
    both `value == null ? "" : value.trim()`
c1  ISSUE-401 follow the optional-column contract from the importer API docs      <- BIC
    normalizeMiddleName returns null for blank values
c2  ISSUE-377 apply the same optional-column contract to the profile fields
    normalizeNickname returns null for blank values, written differently but equivalent
    -> the rival candidate: same change, same shape, one commit closer to the fix
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
- Match that text against the texts of `ISSUE-401` (middle_name) and `ISSUE-377` (nickname),
  which are the only evidence that separates `c1` from `c2`. The subjects carry the
  identifiers only; the identifiers themselves are not ordered or otherwise informative
  (`ISSUE-401` is the BIC, `ISSUE-377` is not, although 377 < 401).
- Report exactly `{c1}`, and not `c3`, which every blame variant reaches, nor `c2`.

A tool that reconstructs the call graph across `c3` can also reach `c1`, because `middleName`
called `normalizeMiddleName` before the deduplication. The scenario claims only that no
*line-level* evidence separates `c1` from `c2`.

## Behaviour check (measured)

`middleName(String[])` and `nickname(String[])` were run on the values
`{null, "", " ", "   ", "x", " x ", "Ann", "  Ann  "}` — 16 probes per snapshot.

- `c1` (BIC) differs from `c0` on **4** probes: the four blank or `null` middle names now
  come back as `null` instead of `""`.
- `c2` differs from `c1` on **4** probes, all of them nicknames — a real, intended behaviour
  change written in a different but equivalent form (`value.isBlank()` instead of
  `value.trim().isEmpty()`).
- `c3` is **identical to `c2`** on all 16 probes, i.e. the deduplication really preserves
  behaviour, although its body (`String trimmed = ...; return trimmed.isEmpty() ? null : trimmed;`)
  is textually a third variant.
- `c4` (BFC) differs from `c3` on exactly the **4** middle-name probes and restores `c0`'s
  middle-name contract; it differs from `c0` on exactly the **4** nickname probes, i.e. it
  keeps `c2`'s intended change and undoes nothing else.

All five commit snapshots compile with `javac` (JDK 25): 0 failures out of 5.

## Required graph-schema features

- Factors: issues, context
- Operation types: write_file, replace
- Expected SZZ policy is defined in `expected_szz`.
- The four issue texts are scenario metadata under the top-level `issues:` key; the
  repository carries only the identifiers in the commit subjects. An external context
  interface is designed in issue #23.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0102/
|-- scenario.graph.yml
`-- README.md
```

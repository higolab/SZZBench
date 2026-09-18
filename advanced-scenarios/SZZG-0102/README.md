# SZZG-0102: Issue description required

## Source

- Category: Issue, message, context, and non-local evidence (G7)

## Purpose

Evaluate whether SZZ can use the **issue identifier carried by the fix message**, and the
issue text behind it, to choose the commit that changed optional-name normalization over the
importer cleanups that line-based blame reaches.

Before this repair, no commit message carried `ISSUE-482` at all (the issue existed only in
the YAML, so a Git-only tool could not even find it), and plain blame reached the BIC
directly, so no context was needed (issue #4).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the CSV contact importer
    normalizeOptional -> value == null ? "" : value.trim()
c1  Store missing optional contact columns as null                     <- BIC (no issue id: it predates the report)
    normalizeOptional now returns null for blank values
c2  ISSUE-377 strip the spaces from imported postal codes              unrelated field, own ticket
c3  ISSUE-510 group the CSV field normalizers in a nested helper       behaviour-preserving restructuring
    normalizeOptional moves into `private static final class Fields`, so the faulty line is re-indented
c4  ISSUE-482 keep blank middle names as empty strings                 <- BFC
```

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c4`
- `related_but_not_correct`: `c2` (the unrelated postal-code cleanup), `c3` (the commit plain
  blame actually reaches)

## Measured plain-blame outcome at BFC^

`BFC^` is `c3`. The BFC deletes exactly one line:

```text
src/main/java/example/CsvContactImporter.java:14
  "      return value == null || value.trim().isEmpty() ? null : value.trim();"  ->  c3
```

Outcome: **miss** (with one extra). `git blame` reaches `c3`, the restructuring commit,
because moving the helper into the nested class re-indented the line; the required BIC `c1`
is not reached. Generation therefore prints, by design:

```text
[WARNING] GW703: bug B001: basic git blame reaches 1194ea77..., not expected graph BIC hash(es).
```

`1194ea77` is `c3`.

## What a tool must do to pass

- Read `ISSUE-482` from the BFC message (`git log` alone now suffices to find the identifier)
  and look the issue up.
- Use the issue text — exports contain `null` since blank optional columns started to be
  *stored as null* — to select `c1`, whose message says exactly that, over the two nearby
  cleanups. `c2` touches a different field (`ISSUE-377`, postal codes) and `c3` is a
  behaviour-preserving restructuring (`ISSUE-510`).
- Report exactly `{c1}`; in particular not `c3`, although that is where line-based blame
  lands.

Note: the repository carries only the *identifiers*. The issue title and description live in
the scenario's `issues:` block; an external context interface for handing them to a tool is
designed in issue #23 and deliberately not invented here.

## Behaviour check (measured)

`CsvContactImporter.middleName(String[])` on middle-name columns
`{"", " ", "   ", "\t", "Lee", " Lee ", "  Van  Dijk ", null}` and
`CsvContactImporter.postalCode(String[])` on postal columns
`{"", " ", "SW1A 1AA", " sw1a  1aa ", "12345", "  ", null}` (15 probes; the methods take
string columns, so the domain is blank, whitespace-only, padded, ordinary and `null` values
rather than integer limits).

- `c1` (BIC) differs from `c0` on 5 probes: every blank middle name is imported as `null`
  instead of `""`.
- `c2` adds its own, independent change on 2 `postalCode` probes.
- `c3` is **identical to `c2`** on all 15 probes: the restructuring preserves behaviour.
- `c4` (BFC) agrees with `c0` on **all 8 `middleName` probes**, i.e. the bug's contract is
  fully restored. It still differs on the 2 `postalCode` probes, which is the deliberate,
  unrelated change made by `c2` and not part of this bug.

## Required graph-schema features

- Factors: issues, context
- Operation types: write_file, replace
- Expected SZZ policy is defined in `expected_szz`.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0102/
|-- scenario.graph.yml
`-- README.md
```

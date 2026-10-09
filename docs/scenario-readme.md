# Scenario READMEs: the generated header and the prose

Every scenario directory carries a `README.md` next to its scenario file. The
README has two parts with two owners.

## The header is generated

The file opens with a header that `szzbench readme` renders from the scenario
file: the `# <id>: <title>` line and a metadata table between two marker
comments.

```markdown
# SZZG-0022: Copy propagation with direct and origin BIC evaluation variants

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `direct-bic`, `origin-bic`, `evaluation-variant`, `relaxed-with-credit` |
| oracle | default (`direct-only`): `exact_set`; required `c2`; related origins `c1` · `origin-aware`: … · BFC `c3` |
| graph features | 2 BICs; origin faults; 3 evaluation variants (`direct-only`, `origin-aware`, `relaxed-with-credit`); `clone_relationships`; `copy_relationships` |
<!-- /szzbench:header -->
```

| row | source | notes |
|---|---|---|
| title | `meta.id`, `meta.title` | the same title the index mirrors (`IE041`) |
| `category` | `meta.category_code`, `meta.category` | the one category vocabulary of both suites (`decisions/vocabulary.md` §3) |
| `tier`, `status`, `difficulty` | `meta.*` | see `decisions/vocabulary.md` §4 and §7 |
| `language` | `repository.language` | `java` or `python` today |
| `factors` | `meta.factors` | the controlled vocabulary of `decisions/vocabulary.md` §1 |
| `oracle` | the evaluator's own policy resolution (`_commit_level_policy`) | the default variant first, then every other declared variant; an inferred direct BIC, a `top_k` ranking oracle and an `expect_no_bic` contract appear exactly as a scored run reads them, followed by the BFC ids and, when declared, the branch-level entries (`main → c1 (BFC c3)`) |
| `defeats` (when declared) | `meta.defeats` | the cheap-rule families the scenario is built to make fail (`decisions/vocabulary.md` §8), checked by `szzbench baselines` |
| `graph features` (graph suite only) | the scenario file | what the scenario uses that the classic schema cannot express: branches and merges, replayed commits (`rebase_of`, `cherry_pick_of`, …), generated commits, the ref lifecycle, operations beyond `write_file`/`replace`, several bugs, BICs, BFCs or fault sites, origin faults, a policy other than `exact_set`, evaluation variants, oracle levels beyond commit and line, and context sections (`issues`, `work_items`, …). A linear single-bug exact-set scenario says so: it is in the graph suite for its category, not for a feature |

Nothing in the header is typed by hand, so nothing in it can drift from the
scenario. Before the header existed the README repeated `meta.factors` under a
`## Factors` heading and named the category under `## Source`; on 2026-09-22
eight of those factor lists no longer matched the YAML and 35 category labels
came from a vocabulary the index had dropped (issue #19). Those sections are
gone: `szzbench readme --write` removes them, and the lint below reports one
that comes back.

## The prose is the author's

Everything after the end marker is written by the scenario's author and is
never touched by a tool: the purpose, the commit structure, what a tool must
do to pass, and the evidence — behaviour at each commit, the blame of the
lines the fix deletes, counterfactuals — that the oracle is right.
`szzbench readme --write` replaces the header and leaves the body byte for
byte, blank lines included; the exceptions are a real `## Factors` or
`## Source` section and the leftovers of an old header (see below), which it
removes. A heading quoted inside a fenced code
block (backticks or tildes) is text, not a section, and is left alone. The
sections vary by scenario because the evidence does; the skeleton
`new-scenario` / `new-graph-scenario` writes proposes `## Purpose`,
`## Commit structure` (`## Expected history` in the graph suite) and
`## Expected behavior` / `## Expected BIC / BFC`.

One prose block is checked all the same: a graph README's `## Expected history`
block, whose parenthesised operation lists are a copy of `commits[].operations`
and are compared with them by `GW454`.

## A malformed header, a second header, BOM and CRLF

The header is recognised by its exact shape: the title line, one blank line,
the begin marker, table rows, the end marker. A README whose header has been
edited out of that shape still has a header, found by its first marker line
outside fenced code however that marker is spelled. It is reported as
`header is malformed: …` with what is wrong — two blank lines or none under
the title, text before the title line, no end marker, a marker spelled
differently (`<!-- /SZZBench:header -->`, trailing whitespace), a blank line
inside the table — and `--write` replaces it whole: from the start of the file
through its end marker, or through its last table row when the end marker is
missing. Text above the title line, or between it and the begin marker, is not
dropped; it becomes the first paragraph of the body, under the new header.
Everything after the old header is kept byte for byte.

A README carries one header. A second one in the body (a begin marker with its
table, its end marker and the title line above it) or a stray end marker is
reported as `carries a second header at line N` (or `a stray header end
marker`), and `--write` removes it the way it removes a `## Factors` copy.
Markers quoted inside fenced code, or in indented code (a line indented by four or more spaces, or by a tab), are text. Until issue #184 a malformed
header was reported as missing, `--write` put a new header above the old one,
and the doubled README then passed every check.

A UTF-8 BOM and CRLF line endings are not a difference: the README is compared
without the BOM and with LF endings, so a checkout made with
`core.autocrlf=true` is current. `--write` keeps both: a leading BOM stays in
front, and the header is written with the line ending of the file's first
line, so a CRLF README gets no LF lines.

`--write` reads back what it wrote and checks it again. A README still stale
afterwards is listed under `still stale after the write`, and the command
exits with 1. A header the scenario would render out of shape — a field value
with a line break — is not written at all (`not written`). A line break or a
run of whitespace in `meta.title` is rendered as one space. A README that is
not valid UTF-8 is listed as unreadable (an `error:` line, exit 1).

## Keeping the two in step

```sh
szzbench readme                    # check every README of both suites; exit 1 when one is stale
szzbench readme --write            # regenerate the stale, malformed or missing headers
szzbench readme --write advanced-scenarios/SZZG-0022   # one scenario (file or directory)
```

`validate --lint` and `validate-graph --lint` report the same disagreement as
`W455` / `GW455`: the header is missing, it is malformed (the message says
how), it differs from what the scenario renders (the message quotes the first
differing line), a second header is left in the body, or a hand-written
`## Factors` / `## Source` copy is present. `tests/test_readme_header.py`
asserts that every shipped README is current, so a metadata or oracle change
that forgets `szzbench readme --write` fails the test suite.

The header is compared textually, so a scenario edit that changes any row —
a new factor, a corrected oracle, a tier promotion — needs one
`szzbench readme --write` in the same commit.

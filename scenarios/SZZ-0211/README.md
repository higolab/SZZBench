# SZZ-0211: Authorization guard weakened, then rewritten four times before the fix (depth-4 line history with one whitespace-only hop)

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `deep-line-history`, `rewrite-depth-4`, `whitespace-only-hop`, `comment-noise`, `basic-blame-distractor`, `guard-removed` |
| oracle | `exact_set`; required `c1`; known distractors `c2`, `c3`, `c4`, `c5` · BFC `c6` |
<!-- /szzbench:header -->

## Purpose

The deepest line history in the suite (issue #24): four behaviour-preserving
rewrites of the faulty line between the BIC and the BFC, one of them
whitespace-only. The fault is an authorization guard that lost its
`isActive()` half, so inactive accounts may open reports. One-shot blame,
with or without `-w`, stops at the last rewrite; plain recursion reaches the
BIC in four steps; recursion with `-w` skips exactly the whitespace hop and
needs three. The whitespace hop is there to show that `-w` shortens the
chain without replacing the recursion.

## Commit structure

- `c0`: `ReportAccess.mayOpen(user, reportId)` rejects a `null` or inactive account, then requires a
  non-empty report id.
- `c1`: Drops `|| !user.isActive()` from the guard. Inactive accounts pass. This is the **BIC**.
- `c2`: Re-indents the file from two to four spaces. Whitespace only.
- `c3`: Renames the parameter `user` to `account`.
- `c4`: Drops the braces around the single-statement guard.
- `c5`: Appends a trailing comment to the guard line.
- `c6`: Restores the `isActive()` check. This is the **BFC**.

## Expected behavior

The expected BFC is `c6` and the expected BIC is `c1`. `c2` to `c5` are known distractors.

## Behaviour at each commit

`mayOpen(active, "r1")`, `mayOpen(inactive, "r1")`, `mayOpen(null, "r1")`
(`tests/test_deep_line_history.py`):

| commit | active | inactive | null |
|---|---|---|---|
| `c0` | true | false | false |
| `c1` | true | **true** | false |
| `c2` | true | **true** | false |
| `c3` | true | **true** | false |
| `c4` | true | **true** | false |
| `c5` | true | **true** | false |
| `c6` | true | false | false |

## Plain blame outcome

`c6` deletes one line, `if (account == null) return false; // anonymous callers never see reports`,
and `git blame` at `c6^` attributes it to **`c5`**. The line history from there: `c5`'s line replaced
`c4`'s, `c4`'s replaced `c3`'s, `c3`'s replaced `c2`'s re-indented line, and `c2`'s replaced `c1`'s
`if (user == null) {`. Four hops. `git blame -w` at `c6^` still answers `c5` — the comment is not
whitespace — and helps only at the last hop, where it attributes `c2`'s re-indented line to `c1`.

## What a tool must do

Report `c1`. Recursion alone reaches `c1` in four steps; `-w` alone stops at `c5`; a tool that
recurses and blames with `-w` reaches `c1` in three. Stopping at any of `c2` to `c5` — a formatting
commit, a rename, a brace change, a comment — reports a commit that did not change what the guard
accepts.

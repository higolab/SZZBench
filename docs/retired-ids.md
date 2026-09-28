# Retired scenario ids

Scenario ids are stable and are never renumbered (`decisions/vocabulary.md` §5), so a
scenario that is withdrawn leaves a gap. This file records every gap: the id, the title
it carried, why it was withdrawn, and what covers its subject instead.

A withdrawn scenario's directory and index entry are removed in the same commit that
adds its row here.

| id | former title | reason | replacement |
|---|---|---|---|
| SZZ-0058 | Resource close omission | The title was never true: the repository holds no resource and no `close()`, only `if (opened) { return false; }` added by the BFC — the same `if (<cond>) { return false; }` omission shape as SZZ-0053 and SZZ-0076, whose titles do match their conditions (SZZ-0070 carried it too until it was repaired into a transition table on 2026-09-28; SZZ-0047 omits a null check and returns a default rather than `false`). Neither remedy in `decisions/consolidation-matrix.md` §2 works now: rewriting it around a real `Closeable` would duplicate SZZ-0189, and retitling it would leave a fourth copy of a shape three scenarios already cover. | SZZ-0189 covers a real missing `close()` on a `BufferedWriter`; SZZ-0053 and SZZ-0076 cover the guard-omission shape, and SZZ-0047 the null-check omission. |
| SZZ-0167 | Patch context required | Duplicate of SZZ-0160: same category (S7), same caller/callee shape, and in both the BIC and the BFC edited only the callee's boundary line, so neither actually required the caller for context. SZZ-0167 was the weaker of the two — two commits with no initial commit, the stock `Range.contains` template, a single vague `context` factor, and `difficulty: hard` that nothing justified. Recorded as a delete candidate in `decisions/consolidation-matrix.md` §2. | The caller/callee shape it shared with SZZ-0160 is kept by SZZ-0160, now titled for what it is. A fix that genuinely lives in the caller while the BIC sits in the callee is SZZ-0169. |
| SZZ-0082 | Formatting-only rewrite after bug introduction | Duplicate of SZZ-0081, recorded in `decisions/consolidation-matrix.md` §3 as "same 2-line split of the faulty expression — **merge (keep 0081)**" and never executed. The two declare the same six factors, run the same four-commit shape (initial, boundary BIC, formatting-only commit, fix), and are solved and missed by the same rules; they differ in the class and variable names. Confirmed again in 2026-09-25 by an outcome vector over twelve cheap baselines and PyDriller 2.12, in which the two are identical. | SZZ-0081 keeps the formatting-after-BIC shape. SZZ-0083 keeps the variant a `blame -w` recovers, which is the discriminator between the two blame configurations. |
| SZZ-0120 | BFC with unrelated helper addition | Duplicate of SZZ-0115, recorded in `decisions/consolidation-matrix.md` §3 as "BFC adds helper — visible difference: none — **merge**" and never executed. Same four factors, same three-commit shape, same oracle and the same outcome under every predictor measured; its description was the generated boilerplate ("evaluates SZZ behavior when the bug-fixing commit has the shape: …"). | SZZ-0115 keeps the tangled-BFC shape under its own name. |

## Migrating an existing checkout

Retiring a scenario removes its source and index entry, but `generated-input-repos/` is
derived output that Git does not track, so an existing checkout keeps
`generated-input-repos/<id>/` for every retired id. Nothing regenerates or removes it:
`szzbench generate-all-repos` visits only scenario files, with or without `--overwrite`.

Such a directory is an **orphan**. After pulling a change that retires a scenario:

- `szzbench generate-all-repos` lists orphans under `Orphaned:` in its summary and
  prints a warning naming each one. It does not delete them.
- `szzbench baselines`, `szzbench coverage` and `szzbench evaluate --include-generated`
  skip an orphan with a warning instead of failing; the id does not count towards the
  suite. An id that a predictions file names explicitly is still an error, because that
  is a claim about a scenario, not a leftover directory.
- To remove them, delete the directories (`rm -rf generated-input-repos/SZZ-0058
  generated-input-repos/SZZ-0167`) or run `szzbench clean` and regenerate everything.

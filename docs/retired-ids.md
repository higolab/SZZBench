# Retired scenario ids

Scenario ids are stable and are never renumbered (`decisions/vocabulary.md` §5), so a
scenario that is withdrawn leaves a gap. This file records every gap: the id, the title
it carried, why it was withdrawn, and what covers its subject instead.

A withdrawn scenario's directory and index entry are removed in the same commit that
adds its row here.

| id | former title | reason | replacement |
|---|---|---|---|
| SZZ-0167 | Patch context required | Duplicate of SZZ-0160: same category (S7), same caller/callee shape, and in both the BIC and the BFC edited only the callee's boundary line, so neither actually required the caller for context. SZZ-0167 was the weaker of the two — two commits with no initial commit, the stock `Range.contains` template, a single vague `context` factor, and `difficulty: hard` that nothing justified. Recorded as a delete candidate in `decisions/consolidation-matrix.md` §2. | The caller/callee shape it shared with SZZ-0160 is kept by SZZ-0160, now titled for what it is. A fix that genuinely lives in the caller while the BIC sits in the callee is SZZ-0169. |

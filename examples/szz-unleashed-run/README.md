# A complete run: SZZ Unleashed over the shipped suite, at two depths

This directory holds two runs of SZZ Unleashed over every scenario SZZBench ships: one at the depth
SZZ Unleashed uses by default, 3, and one at depth 1. Each has the predictions it made and the
report SZZBench wrote. It is a companion of [../pydriller-run/](../pydriller-run/README.md) and
[../pyszz-run/](../pyszz-run/README.md): the runs re-score without the tool installed. The
difference between the two depths is the most striking result here, so both are kept.

- **Tool**: SZZ Unleashed's bug-introducer finder (the `szz` directory of
  [wogscpar/SZZUnleashed](https://github.com/wogscpar/SZZUnleashed) at commit `79f369f`, MIT
  licensed), built with `tools/adapters/szz_unleashed_pom.xml` and run through
  `tools/adapters/szz_unleashed_to_predictions.py --jar`
- **Suite**: 279 scenarios (133 classic, 146 graph)
- **Measured**: 2026-09-30 on macOS 26.3 (Apple silicon), Java 25.0.2, Git 2.50.1; the jar's
  SHA-256 was `6b1700282b8676247ba4b99dc6c44709d441d892e03be9e75db75bf3819694e1`

## Building SZZ Unleashed

SZZ Unleashed builds with Gradle 4.10.3 and Java 8. Its `build.gradle` uses the `compile`
configuration, which Gradle 7 removed. `tools/adapters/szz_unleashed_pom.xml` builds the same jar
with Maven: the same dependency versions, `Main` as the entry point, and the signature files of the
signed dependencies left out of the merged jar, as the Gradle build does. The bytecode targets
Java 8 and runs on a current JDK.

```bash
git clone https://github.com/wogscpar/SZZUnleashed.git
git -C SZZUnleashed checkout 79f369f
cp tools/adapters/szz_unleashed_pom.xml SZZUnleashed/szz/pom.xml
mvn -q -f SZZUnleashed/szz/pom.xml package
```

The jar is `SZZUnleashed/szz/target/szz_find_bug_introducers-0.1.jar`.

## The commands

```bash
szzbench generate-all-repos

tools/adapters/szz_unleashed_to_predictions.py \
    --jar SZZUnleashed/szz/target/szz_find_bug_introducers-0.1.jar \
    --generated-root generated-input-repos \
    --out results/szz-unleashed/depth-3/predictions.jsonl

tools/adapters/szz_unleashed_to_predictions.py \
    --jar SZZUnleashed/szz/target/szz_find_bug_introducers-0.1.jar \
    --depth 1 \
    --generated-root generated-input-repos \
    --out results/szz-unleashed/depth-1/predictions.jsonl

for depth in 3 1; do
    szzbench evaluate \
        --predictions results/szz-unleashed/depth-$depth/predictions.jsonl \
        --generated-root generated-input-repos \
        --include-generated \
        --out results/szz-unleashed/depth-$depth
done
```

Each run took about 36 seconds. For every scenario, the adapter writes SZZ Unleashed's issue list, its
output and its log under `generated-input-repos/<SCENARIO_ID>/default/szz-unleashed/run-depth<depth>/`.
Next to `--out` it writes `szz-unleashed-run.json`, which records the Java version, the jar's
checksum, the depth and any errors. `depth-<depth>/predictions.jsonl` here is that `--out` with the
`raw_file` path removed from every prediction, and `depth-<depth>/evaluation-results.md` is the
report the evaluation wrote.

## What SZZ Unleashed is given

SZZ Unleashed reads the bug-fixing commits from an issue list. Each entry names a fix and the dates
of its issue. Its default finder (`SIMPLE`) keeps a candidate as bug-inducing when it was committed
before the issue was reported, and sets the other candidates aside as partial-fix suspects.

SZZBench's scenarios record no bug reports. The adapter therefore writes one entry per bug-fixing
commit and gives the fix's own committer date as the report date. No two commits of a generated
repository share a committer time, so every candidate, being an ancestor of the fix, was committed
strictly before it and passes the filter. This is the counterpart of the
`issue_date_filter: false` the [PySZZ run](../pyszz-run/README.md) uses.

## What it scores

| | PASS | `control` | `discriminating` | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|---|
| SZZ Unleashed, depth 3 (its default) | **28** | 24 / 233 | **4 / 46** | 263 | 245 | 78 | 0.518 | 0.771 |
| SZZ Unleashed, depth 1 | **156** | 156 / 233 | 0 / 46 | 228 | 70 | 113 | 0.765 | 0.669 |
| *`blame-deleted-lines`* ([floor](../../docs/baselines.md)) | 156 | | | | | | | |
| *PySZZ's B-SZZ* ([../pyszz-run/](../pyszz-run/README.md)) | 156 | 156 / 233 | 0 / 46 | 229 | 72 | 112 | 0.761 | 0.672 |
| *PyDriller 2.12* ([../pydriller-run/](../pydriller-run/README.md)) | 161 | 160 / 233 | 1 / 46 | 235 | 66 | 106 | 0.781 | 0.689 |

Neither run reported a tool error. Each depth was run three times, and every run gave the same
answer on all 279 scenarios.

## What the depth changes

- **At depth 1, SZZ Unleashed blames the deleted lines, and little else.** It passes 156, as
  `blame-deleted-lines` does, and shares 155 of them. It gains SZZG-0109 (file deletion) and loses
  SZZG-0021 (clone removal as fix), where it answers nothing. It shares 154 scenarios with PySZZ's
  B-SZZ and 153 with PyDriller.
- **At depth 3, it follows each blamed line two more layers back through its line mapping graph and
  reports every commit on the way.** Recall rises from 0.669 to 0.771, precision falls from 0.765
  to 0.518, and it passes 28.
  - Of its 251 failures, 178 contain every required commit and others besides; in 152 of those, the
    extra commits include the initial commit `c0`. The remaining 73 miss a required commit.
  - It passes five scenarios that depth 1 fails. Four are `discriminating`: SZZ-0136, SZZG-0028,
    SZZG-0069 and SZZG-0076. Each has a two-commit oracle; depth 1 answers one of the two commits
    and depth 3 answers both. Token-level B-SZZ ([../token-bszz-run/](../token-bszz-run/README.md))
    passes all four too; no other run under `examples/` passes them, and no naive rule does. The
    fifth is SZZG-0140, a `top_k` oracle whose first-ranked answer must be `c1`.

One parameter therefore moves SZZ Unleashed from a near-copy of the blame baseline to four
`discriminating` passes, more than any other recorded run except token-level B-SZZ (11). The cost
is 132 `control` scenarios.
This is the trade the tiers are built to show: a `control` checks an input condition one commit at a
time, and a `discriminating` scenario needs more than one commit that plain blame does not reach.

## What these numbers depend on

- **The depth.** The adapter's default is SZZ Unleashed's own, 3.
- **The issue dates.** They are described above. With real report dates, the `SIMPLE` finder would
  set candidates committed after the report aside, which the scenarios give it no reason to do.
- **Git's configuration.** JGit reads the configuration under Java's `user.home`, and git reads
  `HOME`. The adapter points both at an empty directory and withholds every `GIT_*` variable, as
  SZZBench's generator does (issue #96).
- **Failures.** SZZ Unleashed prints an exception and carries on: a date it cannot parse, for
  example, becomes a stack trace, and the candidate is treated as outside the timeframe. The adapter
  therefore fails a scenario as a tool error when the run exits non-zero, writes no
  `fix_and_introducers_pairs.json`, or prints a stack trace. None of that happened in these runs.

## Reproducing it

The generator is deterministic, so the hashes in the `predictions.jsonl` files match a fresh
`generate-all-repos` on the same scenarios, and `szzbench evaluate` re-scores them without SZZ
Unleashed or Java. Re-running the adapter with the same jar reproduces the predictions themselves.

## What this is not

This is SZZ Unleashed's SZZ phase 2, finding the bug-inducing commits of known fixes, with its
default `SIMPLE` finder. It is not its phase 1, which links fixes to issues. It is also not the
random-forest classifier of risky commits that the repository ships beside the finder.

#!/bin/sh
# Rewrites every generated repository under /in into a token-level history under /out, the way
# the MV-SZZ replication package prepares its N-token repositories
# (scripts/data_preparation/apply_cregit/*/run_cregit_<N>token.sh): the BFG fork runs cregit's
# tokenBySha.pl on every .java blob, and the working tree is reset to the rewritten HEAD.
#
# Runs inside the image built from this directory's Dockerfile, with
#   /in           the generated-input-repos root (read-only)
#   /out          where the token-level repositories go
#   /opt/cregit   the replication package's modified cregit (tools/cregit.zip), read-only
# and BFG_WINDOW_SIZE (default 1) tokens per line. For each <id>/<variant> it writes repo/,
# tokenize.log and tokenize.status (the exit status, 0 when both steps succeeded).
set -u

VARIANT="${VARIANT:-default}"
BFG_WINDOW_SIZE="${BFG_WINDOW_SIZE:-1}"
export BFG_WINDOW_SIZE
BFG_JAR=$(ls /opt/bfg-repo-cleaner/bfg/target/bfg-*.jar | head -n 1)
export BFG_TOKENIZE_CMD="/opt/cregit/tokenize/tokenizeSrcMl.pl --srcml2token=/opt/cregit/tokenize/srcMLtoken/srcml2token --srcml=srcml --ctags=ctags"
# tokenBySha.pl memoizes by blob content only, so one directory per window size
export BFG_MEMO_DIR="/out/.memo-window-$BFG_WINDOW_SIZE"
mkdir -p "$BFG_MEMO_DIR"

for repo in /in/*/"$VARIANT"/repo; do
    [ -d "$repo" ] || continue
    id=$(basename "$(dirname "$(dirname "$repo")")")
    out="/out/$id/$VARIANT"
    rm -rf "$out"
    mkdir -p "$out"
    # BFG runs from its own checkout, as the replication package's script does: the fork opens
    # the repository of the current directory while it parses --blob-exec, and fails with
    # "None.get" outside one. tokenBySha.pl also writes its temporary files there.
    # With several processors BFG runs tokenBySha.pl on several blobs at once, and a run over
    # the shipped suite once stopped for good with two of them waiting for their input; one
    # processor rewrites the same history one blob at a time. The time limit and one retry
    # are the safety net for any other hang.
    for attempt in 1 2; do
        rm -rf "$out/repo"
        cp -a "$repo" "$out/repo"
        (
            cd /opt/bfg-repo-cleaner \
            && timeout "${BFG_TIMEOUT:-600}" java -XX:ActiveProcessorCount=1 -jar "$BFG_JAR" \
                "--blob-exec:/opt/cregit/tokenizeByBlobId/tokenBySha.pl=\.java$" \
                --no-blob-protection "$out/repo" \
            && cd "$out/repo" \
            && git reset --quiet --hard HEAD
        ) > "$out/tokenize.log" 2>&1
        status=$?
        # retry only a run that timed out
        [ "$status" -eq 124 ] || break
        echo "attempt $attempt timed out" >> "$out/tokenize.attempts"
    done
    # BFG exits 0 even when it rejects its arguments, so the log has to say that it ran:
    # either it rewrote the history, or there was nothing to rewrite (no .java blob changed)
    if [ "$status" -eq 0 ] \
        && ! grep -q -e "BFG run is complete" -e "no dirty commits found" "$out/tokenize.log"; then
        status=3
    fi
    echo "$status" > "$out/tokenize.status"
done

#!/usr/bin/env bash
# Convenience driver for the review-code regression fixture set.
# It does NOT run the review (that's LLM-driven via /review-code) — it lists the
# fixtures and prints the pass criteria so you can run and compare quickly.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== real-bugs/ (MUST be caught — recall) =="
for f in "$DIR"/real-bugs/*.py; do echo "  $f"; done
echo
echo "== traps/ (MUST NOT be flagged — precision) =="
for f in "$DIR"/traps/*.py; do echo "  $f"; done
echo
echo "== clean/ (baseline — Approve) =="
for f in "$DIR"/clean/*.py; do echo "  $f"; done
echo
echo "Run each group through /review-code and compare against expected.md:"
echo "  /review-code $DIR/real-bugs   -> every intended finding present, verdict Changes Requested/Blocked"
echo "  /review-code $DIR/traps       -> ZERO findings, verdict Approve"
echo "  /review-code $DIR/clean       -> ZERO findings, verdict Approve"

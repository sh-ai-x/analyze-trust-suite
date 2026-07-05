#!/usr/bin/env bash
# Convenience driver for the security-scan regression fixture set.
# It does NOT run the scan (that's LLM-driven via /security-scan) — it lists the
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
echo "Run each group through /security-scan and compare against expected.md:"
echo "  /security-scan $DIR/real-bugs   -> every intended finding present"
echo "  /security-scan $DIR/traps       -> ZERO findings"
echo "  /security-scan $DIR/clean       -> ZERO findings"
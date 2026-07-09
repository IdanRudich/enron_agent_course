#!/usr/bin/env bash
# Issue 12 manual smoke path — real Minimax integration for reference agent + judge.
# Usage:
#   1. Copy .env.example to .env and fill in credentials, OR export vars directly.
#   2. source .env   # if using .env
#   3. ./scripts/minimax_smoke.sh [easy|single|full]
#
# Phases:
#   single (default) — one easy challenge via enron-eval
#   easy             — all 10 easy challenges
#   full             — all 28 challenges (slow, uses judge on mismatches)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

require_var() {
  if [[ -z "${!1:-}" ]]; then
    echo "Missing required env var: $1" >&2
    exit 1
  fi
}

require_var ENRON_AGENT_API_KEY
require_var ENRON_AGENT_MODEL
require_var ENRON_JUDGE_API_KEY
require_var ENRON_JUDGE_MODEL

export ENRON_AGENT_BASE_URL="${ENRON_AGENT_BASE_URL:-https://api.minimax.io/v1}"
export ENRON_JUDGE_BASE_URL="${ENRON_JUDGE_BASE_URL:-https://api.minimax.io/v1}"

VENV="${ROOT}/.venv"
if [[ -x "${VENV}/bin/enron-eval" ]]; then
  EVAL="${VENV}/bin/enron-eval"
  REF="${VENV}/bin/enron-reference"
else
  EVAL="enron-eval"
  REF="enron-reference"
fi

PHASE="${1:-single}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_BASE="/tmp/enron-smoke-${STAMP}"

echo "=== metadata ===" >&2
"$REF" metadata

echo "=== index ===" >&2
INDEX_DIR="${OUT_BASE}-index"
mkdir -p "$INDEX_DIR"
"$REF" index student_dataset "$INDEX_DIR" >&2

echo "=== single prompt (easy-001) ===" >&2
"$REF" prompt student_dataset "$INDEX_DIR" easy-001 | head -c 500
echo "" >&2

run_eval() {
  local label="$1"
  shift
  local out="${OUT_BASE}-${label}"
  echo "=== enron-eval: ${label} -> ${out} ===" >&2
  "$EVAL" \
    --agent-cmd "$REF" \
    --dataset student_dataset \
    --output-dir "$out" \
    "$@"
  echo "Results: ${out}/results.json" >&2
}

case "$PHASE" in
  single)
    run_eval single --challenge-id easy-001
    ;;
  easy)
    run_eval easy --difficulty easy
    ;;
  full)
    run_eval full --all
    ;;
  *)
    echo "Unknown phase: $PHASE (use single, easy, or full)" >&2
    exit 1
    ;;
esac

echo "=== done ===" >&2

#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
SCENARIOS=(high5xx timeout crashloop deploy_regression)

for scenario in "${SCENARIOS[@]}"; do
  echo
  echo "=============================="
  echo "Demo scenario: $scenario"
  echo "=============================="
  WAIT_SECONDS="${WAIT_SECONDS:-40}" "$DEPLOY_DIR/test_incident.sh" "$scenario"
  sleep 5
done

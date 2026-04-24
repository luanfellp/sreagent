#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$DEPLOY_DIR/docker-compose.local.yml"
SCENARIO="${1:-high5xx}"
WAIT_SECONDS="${WAIT_SECONDS:-40}"

case "$SCENARIO" in
  high5xx|timeout|crashloop|deploy_regression|normal) ;;
  *)
    echo "Uso: $0 [high5xx|timeout|crashloop|deploy_regression|normal]"
    exit 1
    ;;
esac

echo "Ensure services are up (prometheus, alertmanager, loki, promtail, metrics-generator, sreagent)"
docker compose -f "$COMPOSE" ps

echo "Ativando cenário: $SCENARIO"
curl -sS -X POST "http://localhost:8001/scenario?name=$SCENARIO" | jq '.' || true

echo "Aguardando ${WAIT_SECONDS}s para scrape/evaluation/alert delivery..."
sleep "$WAIT_SECONDS"

echo "Alertas ativos no Alertmanager:"
curl -sS http://localhost:9093/api/v2/alerts | jq '.' || true

echo "Status atual do fake service:"
curl -sS http://localhost:8001/health | jq '{scenario, seconds_since_change, config: .config}' || true

echo "Logs recentes no Loki (via labels checkout/prod):"
curl -sG 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={service="checkout",environment="prod"}' \
  --data-urlencode 'limit=5' \
  --data-urlencode 'direction=backward' | jq '.data.result[0:2]' || true

echo "Logs recentes do SREAgent:"
docker compose -f "$COMPOSE" logs --no-color sreagent --tail 120 || true

echo "Resetando cenário para normal..."
curl -sS -X POST 'http://localhost:8001/scenario/reset' || true

echo "Done."

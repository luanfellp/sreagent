#!/usr/bin/env bash
# send_fake_alerts.sh — envia alertas fictícios ao endpoint /alerts/alertmanager
# Uso: ./send_fake_alerts.sh [AGENT_URL]
# Ex: ./send_fake_alerts.sh http://localhost:8000

AGENT_URL=${1:-http://localhost:8000}
ENDPOINT="$AGENT_URL/alerts/alertmanager"

echo "Enviando alertas para $ENDPOINT"

# 1) High 5xx rate (service error)
cat <<'JSON' > /tmp/alert_high5xx.json
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook",
  "groupLabels": {"alertname":"High5xxRate"},
  "commonLabels": {"alertname":"High5xxRate","service":"checkout","severity":"critical"},
  "commonAnnotations": {"summary":"High 5xx error rate for checkout"},
  "externalURL": "http://alertmanager.example.com",
  "alerts": [
    {
      "status": "firing",
      "labels": {"alertname":"High5xxRate","service":"checkout","instance":"checkout-1","severity":"critical"},
      "annotations": {"description":"5xx rate > 5% for 5m","runbook":"https://runbooks.example.com/high5xx"},
      "startsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus.example.org/graph?g0.expr=rate%285xx%5B5m%5D%29>0.05"
    }
  ]
}
JSON

# 2) Telegram send failure (agent-internal alert)
cat <<'JSON' > /tmp/alert_telegram_failure.json
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook",
  "groupLabels": {"alertname":"TelegramSendFailure"},
  "commonLabels": {"alertname":"TelegramSendFailure","service":"sreagent","severity":"medium"},
  "commonAnnotations": {"summary":"Telegram send failures observed"},
  "externalURL": "http://alertmanager.example.com",
  "alerts": [
    {
      "status": "firing",
      "labels": {"alertname":"TelegramSendFailure","service":"sreagent","instance":"sreagent-1","severity":"medium"},
      "annotations": {"description":"sreagent_telegram_send_failure_total increased","runbook":"https://runbooks.example.com/telegram-failures"},
      "startsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus.example.org/graph?g0.expr=sreagent_telegram_send_failure_total%5B5m%5D"
    }
  ]
}
JSON

# 3) Recovery/resolved alert
cat <<'JSON' > /tmp/alert_resolved.json
{
  "version": "4",
  "status": "resolved",
  "receiver": "webhook",
  "groupLabels": {"alertname":"High5xxRate"},
  "commonLabels": {"alertname":"High5xxRate","service":"checkout","severity":"critical"},
  "commonAnnotations": {"summary":"High 5xx error rate resolved"},
  "externalURL": "http://alertmanager.example.com",
  "alerts": [
    {
      "status": "resolved",
      "labels": {"alertname":"High5xxRate","service":"checkout","instance":"checkout-1","severity":"critical"},
      "annotations": {"description":"5xx rate back to normal"},
      "startsAt": "$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)",
      "endsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "generatorURL": "http://prometheus.example.org/graph?g0.expr=rate%285xx%5B5m%5D%29"
    }
  ]
}
JSON

# helper to post and show response
post() {
  local file=$1
  echo "--- POST $file ---"
  curl -s -w "\nHTTP_STATUS:%{http_code}\n" -XPOST -H "Content-Type: application/json" --data-binary "@$file" "$ENDPOINT"
  echo
}

post /tmp/alert_high5xx.json
sleep 1
post /tmp/alert_telegram_failure.json
sleep 1
post /tmp/alert_resolved.json

echo "Done."

# cleanup
rm -f /tmp/alert_high5xx.json /tmp/alert_telegram_failure.json /tmp/alert_resolved.json

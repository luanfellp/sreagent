#!/usr/bin/env bash
# send_bulk_alerts.sh — envia um lote de alertas mistos para testes
# Uso: ./send_bulk_alerts.sh [AGENT_URL] [COUNT]
AGENT_URL=${1:-http://localhost:8002}
COUNT=${2:-10}
ENDPOINT="$AGENT_URL/alerts/alertmanager"
SERVICES=(checkout payments frontend auth inventory)
ALERT_TYPES=(High5xxRate HighLatency DBError TelegramSendFailure)
# Map to allowed severities: critical, high, medium, low, info
SEVERITIES=(critical medium medium critical medium)

echo "Enviando $COUNT alertas para $ENDPOINT"

for i in $(seq 1 $COUNT); do
  idx=$(( (i-1) % ${#SERVICES[@]} ))
  service=${SERVICES[$idx]}
  alert=${ALERT_TYPES[$(( idx % ${#ALERT_TYPES[@]} ))]}
  severity=${SEVERITIES[$(( idx % ${#SEVERITIES[@]} ))]}
  startsAt=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  cat > /tmp/alert_bulk.json <<JSON
{
  "version": "4",
  "status": "firing",
  "receiver": "webhook",
  "groupLabels": {"alertname":"$alert"},
  "commonLabels": {"alertname":"$alert","service":"$service","severity":"$severity"},
  "commonAnnotations": {"summary":"Test alert $alert for $service"},
  "externalURL": "http://alertmanager.example.com",
  "alerts": [
    {
      "status": "firing",
      "labels": {"alertname":"$alert","service":"$service","instance":"$service-$i","severity":"$severity"},
      "annotations": {"description":"Simulated $alert for $service (#$i)"},
      "startsAt": "$startsAt",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus.example.org/graph?g0.expr=simulated"
    }
  ]
}
JSON

  echo "[$i/$COUNT] POST $alert -> $service (severity=$severity)"
  curl -s -w "\nHTTP_STATUS:%{http_code}\n" -XPOST -H "Content-Type: application/json" --data-binary @/tmp/alert_bulk.json "$ENDPOINT"
  echo
  sleep 0.5
done

rm -f /tmp/alert_bulk.json

echo "Lote concluído."

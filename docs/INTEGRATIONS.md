# Integration Setup

SREAgent is read-only. It receives alerts, collects evidence, formats the incident,
and sends notifications. It does not execute remediation.

## Local Demo Defaults

| Tool | URL |
| --- | --- |
| SREAgent API | `http://localhost:8002` |
| SREAgent dashboard | `http://localhost:8002/dashboard` |
| Metrics generator | `http://localhost:8001` |
| Prometheus | `http://localhost:9091` |
| Alertmanager | `http://localhost:9093` |
| Grafana | `http://localhost:3000` |
| Loki | `http://localhost:3100` |
| Zabbix | `http://localhost:8080` |

## Alertmanager

Point Alertmanager to:

```yaml
receivers:
  - name: sreagent-webhook
    webhook_configs:
      - url: http://sreagent:8000/alerts/alertmanager
        send_resolved: true
```

If `SREAGENT_API_TOKEN` is configured, put SREAgent behind a small internal proxy
that adds `X-API-Token`, or use a webhook integration that supports custom headers.

## Prometheus

```env
SREAGENT_PROMETHEUS_URL=http://prometheus:9090
SREAGENT_PROMETHEUS_P95_METRIC=http_request_duration_seconds
```

SREAgent expects request counters with `service`, `environment`, and `code` labels.
The p95 query expects a histogram bucket metric named
`<SREAGENT_PROMETHEUS_P95_METRIC>_bucket`.

## Grafana

```env
SREAGENT_GRAFANA_URL=http://localhost:3000
```

Grafana is used as a link in alert notifications. The local demo provisions
dashboards from `deploy/grafana/dashboards`.

## Loki

```env
SREAGENT_LOKI_URL=http://loki:3100
```

SREAgent queries recent application logs using labels:

```text
service=<service>, environment=<environment>, log_source=application
```

## Kubernetes

For in-cluster execution, SREAgent auto-detects the Kubernetes API through
`KUBERNETES_SERVICE_HOST`. For external execution:

```env
SREAGENT_KUBERNETES_API_URL=https://kubernetes.example.local
SREAGENT_KUBERNETES_NAMESPACE=prod
SREAGENT_KUBERNETES_LABEL_KEY=app
SREAGENT_KUBERNETES_TOKEN_FILE=/run/secrets/kubernetes_token
SREAGENT_KUBERNETES_CA_CERT_FILE=/run/secrets/kubernetes_ca.crt
```

Use `deploy/kubernetes/sreagent-readonly-rbac.yml` as the read-only RBAC baseline.

## Zabbix

```env
SREAGENT_ZABBIX_URL=http://localhost:8080
```

Zabbix is currently linked in notifications and included in the demo stack, but
SREAgent does not query the Zabbix API yet.

## Telegram

```env
SREAGENT_NOTIFICATION_CHANNELS=telegram
SREAGENT_TELEGRAM_CHAT_ID=123456789
SREAGENT_TELEGRAM_BOT_TOKEN_FILE=./secrets/telegram_bot_token.txt
```

You can set `SREAGENT_TELEGRAM_BOT_TOKEN` directly for local experiments, but
secret files are safer for demos.

## WhatsApp Cloud API

```env
SREAGENT_NOTIFICATION_CHANNELS=telegram,whatsapp
SREAGENT_WHATSAPP_PHONE_NUMBER_ID=1234567890
SREAGENT_WHATSAPP_ACCESS_TOKEN_FILE=./secrets/whatsapp_access_token.txt
SREAGENT_WHATSAPP_TO=5511999999999
```

`SREAGENT_WHATSAPP_TO` must be the destination phone number in international
format, without `+`.

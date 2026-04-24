# Demo Stack

## Services

- `SREAgent`: `http://localhost:8002`
- `Grafana`: `http://localhost:3000`
- `Prometheus`: `http://localhost:9091`
- `Alertmanager`: `http://localhost:9093`
- `Loki`: `http://localhost:3100`
- `Fake API / metrics generator`: `http://localhost:8001`
- `Zabbix`: `http://localhost:8080`

## Start the stack

```bash
cp deploy/.env.example deploy/.env
docker compose -f deploy/docker-compose.local.yml up -d --build
```

Telegram is optional. If `SREAGENT_TELEGRAM_CHAT_ID` is empty, the demo still works and the API still returns Telegram-formatted notification previews.

## Available scenarios

- `normal`
- `high5xx`
- `timeout`
- `crashloop`
- `deploy_regression`

## Trigger a scenario

```bash
curl -X POST 'http://localhost:8001/scenario?name=timeout'
```

## Reset to normal

```bash
curl -X POST 'http://localhost:8001/scenario/reset'
```

## Run a demo incident

```bash
bash deploy/test_incident.sh timeout
```

## Run all demo scenarios

```bash
bash deploy/run_demo_scenarios.sh
```

## Demo flow

1. The fake service writes real application logs to `/var/log/demo/checkout-app.log`.
2. Promtail ships those logs to Loki with labels such as `service`, `environment`, and `log_source=application`.
3. Prometheus evaluates latency, 5xx, deploy, and restart rules.
4. Alertmanager sends grouped webhook payloads to SREAgent.
5. SREAgent groups alerts by service, environment, alert name, severity, and status; then queries Prometheus and Loki to build a read-only assessment.
6. The response highlights evidence collected, probable hypothesis, information gaps, suggested next steps, and actions not executed.
7. Telegram delivery is attempted only when configured and never blocks the API path.

## Suggested dashboard

Open `Incident Workbench` in Grafana to present:

- error rate
- p95 latency
- restart count
- active scenario
- recent Loki logs

## Notes

- SREAgent remains strictly read-only.
- Loki is fully integrated in the local demo stack.
- Zabbix is part of the demo environment, but SREAgent does not query it directly yet.
- Local secrets belong in `deploy/secrets/` and must never be committed.

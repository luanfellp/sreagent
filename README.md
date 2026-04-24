# SREAgent

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-api-009688)](https://fastapi.tiangolo.com/)
[![Read-only](https://img.shields.io/badge/mode-read--only-critical)](#security-and-operational-notes)
[![Observability Demo](https://img.shields.io/badge/demo-prometheus%20%2B%20loki%20%2B%20grafana-orange)](#run-the-full-local-demo-stack)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Read-only SRE incident copilot built with Python + FastAPI.

SREAgent receives alerts, correlates evidence from observability sources, produces an initial diagnosis, and formats a clear incident summary for chat surfaces like Telegram. The current local demo uses **Prometheus + Alertmanager + Loki + Grafana** with a fake service that emits both metrics and structured application logs.

---

## Demo in 2 minutes

```bash
git clone https://github.com/luanfellp/sreagent.git
cd sreagent
cp deploy/.env.example deploy/.env
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
docker compose -f deploy/docker-compose.local.yml up -d --build
bash deploy/test_incident.sh timeout
```

What you get:
- fake service emits **metrics + application logs**
- Prometheus evaluates alert rules
- Alertmanager sends webhook to SREAgent
- SREAgent queries **Prometheus + Loki**
- result is formatted as a **PT-BR executive incident summary**

---

## Why this project is different

A lot of “AI for incidents” demos only summarize the alert text.

This one tries to be more honest:
- it is **read-only**
- it uses **deterministic correlation first**
- it queries **real Prometheus signals** in the demo
- it queries **real application logs in Loki** in the demo
- it keeps the LLM as an **advisory layer**, not the source of truth
- it is designed to produce something a human on-call can actually use in the first minutes of an incident

---

## What the project does today

### API capabilities
- Accept alerts through HTTP
- Normalize and enrich incoming alert context
- Query **Prometheus** for service health signals
- Query **Loki** for recent **application logs**
- Apply deterministic correlation rules
- Infer probable component, failure type, and scope
- Produce PT-BR executive summaries suitable for Telegram/WhatsApp
- Draft postmortems from the same evidence pipeline
- Optionally add an LLM refinement layer without replacing deterministic reasoning

### Demo stack capabilities
- Prometheus scraping a fake service and SREAgent metrics
- Alertmanager forwarding alerts to SREAgent
- Loki + Promtail ingesting structured application logs
- Grafana dashboards for incidents, traffic, latency, and Telegram delivery
- Fake incident scenarios:
  - `high5xx`
  - `timeout`
  - `crashloop`
  - `deploy_regression`
  - `normal`

---

## Screenshots / media to add

Recommended assets for a stronger public repo page:
- Grafana **Incident Workbench** screenshot
- terminal run of `deploy/test_incident.sh timeout`
- Telegram message screenshot with the final incident summary
- short GIF showing: scenario trigger → alert → analysis → Telegram delivery

Suggested filenames if you want to add them later:
- `docs/media/grafana-incident-workbench.png`
- `docs/media/telegram-incident-summary.png`
- `docs/media/demo-flow.gif`

Example markdown block for later:

```md
![Incident Workbench](docs/media/grafana-incident-workbench.png)
![Telegram Incident Summary](docs/media/telegram-incident-summary.png)
```

---

## Architecture

```text
Alert Input
   ↓
Normalization
   ↓
Enrichment
   ├─ Prometheus service-health query
   ├─ Loki application-log query
   └─ Workload/demo context
   ↓
Deterministic correlation
   ↓
Diagnosis
   ↓
Optional LLM refinement
   ↓
PT-BR executive summary + notification preview
```

## Local demo flow

```text
Fake service
  ├─ emits Prometheus metrics
  └─ writes structured application logs
        ↓
Prometheus evaluates alert rules
Promtail ships logs to Loki
        ↓
Alertmanager sends webhook to SREAgent
        ↓
SREAgent queries Prometheus + Loki
        ↓
SREAgent returns read-only incident analysis
        ↓
Optional Telegram delivery
```

---

## Stack

### Application
- Python 3.11+
- FastAPI
- Pydantic
- Uvicorn
- httpx
- OpenAI Python SDK (optional)

### Demo / observability
- Prometheus
- Alertmanager
- Loki
- Promtail
- Grafana
- Zabbix
- Docker Compose

---

## Repository structure

```text
sreagent/
├── app/
│   ├── ai/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── integrations/
│   ├── services/
│   ├── dependencies.py
│   └── main.py
├── deploy/
│   ├── alertmanager/
│   ├── grafana/
│   ├── metrics_generator/
│   ├── prometheus/
│   ├── promtail/
│   └── docker-compose.local.yml
├── docs/
├── scripts/
├── tests/
└── README.md
```

---

## Endpoints

### `GET /health`
Basic health check.

### `GET /metrics`
Prometheus metrics for the SREAgent service itself.

### `POST /alerts`
Accepts a normalized alert payload and returns a structured incident assessment.

### `POST /alerts/alertmanager`
Accepts Alertmanager webhook payloads and converts them into SREAgent internal alert input.

### `POST /postmortems/draft`
Builds a draft postmortem from alert input plus timeline context.

---

## Example alert request

```bash
curl -X POST http://127.0.0.1:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "source": "grafana",
    "severity": "critical",
    "message": "Checkout latency is above threshold.",
    "labels": {
      "service": "checkout",
      "environment": "prod"
    }
  }'
```

If `SREAGENT_API_TOKEN` is configured, add:

```bash
-H "X-API-Token: your-token"
```

## Example response shape

```json
{
  "mode": "read-only",
  "status": "analyzed",
  "title": "🟠 Incidente Alto em checkout",
  "signals": {
    "recent_deploy": false,
    "dominant_error": "timeout",
    "restart_detected": true,
    "crashloop_detected": false
  },
  "evidence": [
    {
      "source": "prometheus",
      "kind": "service-health"
    },
    {
      "source": "loki",
      "kind": "application-log-summary"
    }
  ],
  "diagnosis": {
    "probable_component": "checkout",
    "probable_failure_type": "service-degradation",
    "probable_scope": "single-service",
    "confidence": "high"
  },
  "llm_analysis": {
    "summary": "🧠 Análise inicial..."
  }
}
```

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/luanfellp/sreagent.git
cd sreagent
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Run the API only

```bash
uvicorn app.main:app --reload
```

Available at:
- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

---

## Run the full local demo stack

### 1. Prepare local env/secrets

```bash
cp deploy/.env.example deploy/.env
mkdir -p deploy/secrets
printf 'your-telegram-bot-token' > deploy/secrets/telegram_bot_token.txt
```

If you do not want Telegram delivery, leave `SREAGENT_TELEGRAM_CHAT_ID` empty in `deploy/.env` and skip the token file.

### 2. Start the stack

```bash
docker compose -f deploy/docker-compose.local.yml up -d --build
```

### 3. Trigger a scenario

```bash
curl -X POST 'http://localhost:8001/scenario?name=timeout'
```

### 4. Run the demo script

```bash
bash deploy/test_incident.sh timeout
```

### 5. Run all scenarios

```bash
bash deploy/run_demo_scenarios.sh
```

---

## Grafana and demo services

- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9091`
- Alertmanager: `http://localhost:9093`
- Loki: `http://localhost:3100`
- Fake service: `http://localhost:8001`
- SREAgent: `http://localhost:8002`
- Zabbix: `http://localhost:8080`

Recommended dashboard:
- **Incident Workbench**

---

## Configuration

### Core env vars

| Variable | Description | Default |
|---|---|---|
| `SREAGENT_API_TOKEN` | Optional auth token for API endpoints | unset |
| `SREAGENT_READ_ONLY_MODE` | Keeps the service in read-only posture | `true` |
| `SREAGENT_ENABLE_LLM` | Enables optional LLM refinement | `false` |
| `SREAGENT_LLM_PROVIDER` | LLM provider identifier | `openai` |
| `SREAGENT_OPENAI_API_KEY` | OpenAI API key | unset |
| `SREAGENT_OPENAI_MODEL` | OpenAI model name | `gpt-5` |
| `SREAGENT_LLM_TIMEOUT_SECONDS` | Timeout for LLM requests | `15` |
| `SREAGENT_PROMETHEUS_URL` | Prometheus base URL | unset |
| `SREAGENT_PROMETHEUS_P95_METRIC` | Histogram metric base name used for p95 | `http_request_duration_seconds` |
| `SREAGENT_LOKI_URL` | Loki base URL | unset |
| `SREAGENT_TELEGRAM_CHAT_ID` | Optional Telegram target chat | unset |
| `SREAGENT_TELEGRAM_BOT_TOKEN_FILE` | Path to local Telegram bot token file | unset |

---

## Testing

### Unit/integration tests

```bash
pytest -q tests
```

### E2E Alertmanager webhook smoke test

```bash
pytest -q tests/e2e/test_alertmanager_to_agent.py
```

---

## Security and operational notes

- **Read-only by design**: no remediation or infra mutation
- **Secrets must stay local**: use `deploy/.env` and `deploy/secrets/`
- **LLM is advisory only**: deterministic evidence remains the source of truth
- **Kubernetes evidence is still demo-level**: no real cluster provider is wired yet
- **Telegram delivery is optional** and should never require secrets committed to Git

---

## Current status

This project is no longer just a bare API skeleton. It now has a usable local observability demo with:
- real Prometheus queries
- real Loki log lookups
- structured PT-BR incident summaries
- Telegram-ready output
- end-to-end incident scenarios for demos and portfolio usage

---

## Roadmap

- [ ] Add richer multi-service correlation
- [ ] Add real Kubernetes integration
- [ ] Improve diagnosis confidence scoring
- [ ] Store incident history
- [ ] Add PagerDuty/Slack outbound integrations
- [ ] Add CI workflow and quality gates
- [ ] Add screenshots / demo GIFs to the README

---

## Additional docs

- `docs/DEMO_STACK.md` — local demo walkthrough
- `docs/PROJECT_REVIEW.md` — project analysis and next-step roadmap

## License

MIT

---

**Core rule of the project:** collect evidence first, correlate deterministically, and use AI only to refine the final response.

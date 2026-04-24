# SREAgent

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-api-009688)](https://fastapi.tiangolo.com/)
[![Read-only](https://img.shields.io/badge/mode-read--only-critical)](#security-notes)
[![Observability Demo](https://img.shields.io/badge/demo-prometheus%20%2B%20loki%20%2B%20grafana-orange)](#demo-flow)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Read-only SRE incident copilot built with Python + FastAPI.

SREAgent receives alerts, collects evidence from Prometheus, Loki and workload metadata, correlates signals, produces a probable diagnosis, and formats an operational PT-BR summary for humans. The LLM is optional and advisory only. It refines wording and hypotheses, but it does not replace observable evidence.

## Why This Project Exists

Many incident demos only paraphrase alert text.

SREAgent is intentionally different:

- it is read-only by design
- it keeps evidence collection deterministic
- it queries real Prometheus and Loki signals in the local demo
- it treats the LLM as advisory refinement, not source of truth
- it separates collected evidence, probable hypothesis, information gaps, suggested next steps, and actions not executed

## Features

- Receive alerts through HTTP or Alertmanager webhook payloads
- Query Prometheus service health signals
- Query Loki application logs
- Correlate evidence with scoring instead of a single last-write-wins rule
- Produce a probable diagnosis with supporting evidence and information gaps
- Generate read-only PT-BR operational summaries
- Optionally deliver summaries to Telegram in background
- Draft postmortems from the same evidence pipeline

## Architecture

```text
Alert Input / Alertmanager
          |
          v
  Normalization + Grouping
          |
          v
      Enrichment
    | Prometheus |
    | Loki       |
    | Workload   |
          |
          v
 Evidence Scoring Correlation
          |
          v
   Probable Diagnosis
          |
          v
 Optional LLM Refinement
          |
          v
 Read-only Summary + Notification Preview
```

## Repository Structure

```text
sreagent/
├── app/
│   ├── ai/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── integrations/
│   ├── notifications/
│   ├── services/
│   ├── dependencies.py
│   └── main.py
├── deploy/
├── docs/
├── tests/
├── .env.example
├── MANIFEST.in
├── SECURITY.md
└── README.md
```

## Security Notes

- Never commit `.env`, `deploy/.env`, `deploy/secrets/*`, bot tokens, private URLs, or copied local secrets.
- The source distribution excludes local secrets, virtualenvs, caches, workspace notes, and other machine-local files.
- If a Telegram Bot Token was ever exposed, rotate it immediately with `@BotFather` before publishing or reusing the project.
- `SREAGENT_READ_ONLY_MODE=true` is enforced at startup. The application refuses to run in non read-only mode.

More detail: see [`SECURITY.md`](./SECURITY.md).

## Demo In 2 Minutes

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

- fake service emits metrics and structured application logs
- Prometheus evaluates alert rules
- Alertmanager sends webhook payloads to SREAgent
- SREAgent queries Prometheus and Loki
- SREAgent returns a read-only incident assessment
- Telegram delivery happens only if configured; the demo still works without it

## Demo Flow

1. Start the local stack with Docker Compose.
2. Trigger a scenario in the fake service.
3. Prometheus evaluates alerts.
4. Alertmanager sends grouped webhook payloads.
5. SREAgent groups alerts by `service` / `environment` / `severity` / `status`.
6. SREAgent collects evidence from Prometheus, Loki, and workload metadata.
7. Correlation scoring produces a primary hypothesis, confidence, secondary signals, and information gaps.
8. The response highlights evidence collected, probable hypothesis, suggested next steps, and actions not executed.
9. Telegram delivery is attempted only in background and only when configured.

Useful demo commands:

```bash
curl -X POST 'http://localhost:8001/scenario?name=high5xx'
curl -X POST 'http://localhost:8001/scenario?name=timeout'
curl -X POST 'http://localhost:8001/scenario?name=crashloop'
curl -X POST 'http://localhost:8001/scenario?name=deploy_regression'
curl -X POST 'http://localhost:8001/scenario/reset'
```

## API Endpoints

### `GET /health`

Basic health check.

### `GET /metrics`

Prometheus metrics for the SREAgent service itself.

### `POST /alerts`

Accepts a normalized alert payload and returns a structured incident assessment.

### `POST /alerts/alertmanager`

Accepts Alertmanager webhook payloads, groups multiple alerts when needed, and returns a batch response with one result per grouped incident context.

### `POST /postmortems/draft`

Builds a read-only postmortem draft from alert input plus timeline context.

## Read-only Output Contract

The output intentionally separates:

- evidence collected
- primary hypothesis
- secondary signals
- information gaps
- suggested next steps
- actions not executed

This is deliberate. SREAgent must never imply that it executed remediation.

## Telegram Delivery

Telegram delivery is optional.

- If `SREAGENT_TELEGRAM_CHAT_ID` and a bot token are not configured, the API still works.
- Telegram delivery runs through a dedicated notification service and is scheduled in background.
- Failures are logged and exposed as Prometheus counters.
- The project protects itself from a feedback loop on `TelegramSendFailure` alerts.

## Configuration

Safe local application defaults live in `.env.example`.

Demo stack environment defaults live in `deploy/.env.example`.

Important variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SREAGENT_READ_ONLY_MODE` | Enforces read-only startup guardrail | `true` |
| `SREAGENT_API_TOKEN` | Optional API token for protected endpoints | unset |
| `SREAGENT_ENABLE_LLM` | Enables advisory LLM refinement | `false` |
| `SREAGENT_LLM_PROVIDER` | LLM provider name | `openai` |
| `SREAGENT_OPENAI_API_KEY` | OpenAI key for advisory refinement | unset |
| `SREAGENT_PROMETHEUS_URL` | Prometheus base URL | unset |
| `SREAGENT_LOKI_URL` | Loki base URL | unset |
| `SREAGENT_TELEGRAM_CHAT_ID` | Optional Telegram chat target | unset |
| `SREAGENT_TELEGRAM_BOT_TOKEN` | Optional Telegram bot token | unset |
| `SREAGENT_TELEGRAM_BOT_TOKEN_FILE` | Optional bot token file | unset |
| `SREAGENT_ALERTMANAGER_EMIT_RESOLVED` | Returns explicit resolved webhook summaries instead of ignoring them | `false` |

## Development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run lint and tests:

```bash
ruff check .
pytest
pytest -m e2e
```

## Validation Commands

### Tests

```bash
pytest
```

### Lint

```bash
ruff check .
```

### Docker Compose

```bash
docker compose -f deploy/docker-compose.local.yml up -d --build
docker compose -f deploy/docker-compose.local.yml ps
```

### Alert Flow

```bash
bash deploy/test_incident.sh timeout
curl -s http://localhost:8002/health
curl -s http://localhost:9093/api/v2/alerts
```

## Public Demo Packaging

Generate a clean archive from git history only:

```bash
git archive --format=zip --output=sreagent-clean.zip HEAD
```

This avoids shipping `.git`, local `.env` files, secrets, caches, and workspace notes.

## Limitations

- Kubernetes evidence is still mock-based unless a real provider is added.
- Correlation is evidence-scored but still intentionally conservative.
- Telegram delivery is a notification channel, not an incident system of record.
- The LLM can refine wording and prioritization, but it must not be treated as verified root cause.
- The demo includes Zabbix as part of the observability stack, but SREAgent does not yet query it directly.

## LLM Positioning

The LLM is optional and advisory.

- deterministic evidence comes first
- LLM output is sanitized against known evidence ids
- unsupported or failing providers fall back to the mock provider
- the system must still function without any LLM enabled

## Related Docs

- [`SECURITY.md`](./SECURITY.md)
- [`docs/DEMO_STACK.md`](./docs/DEMO_STACK.md)
- [`docs/PROJECT_REVIEW.md`](./docs/PROJECT_REVIEW.md)

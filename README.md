# sreagent

SRE incident copilot built with Python and FastAPI.

`sreagent` is a read-only incident analysis API designed to help SRE, platform, and on-call teams turn alerts into structured, evidence-backed incident assessments. It enriches incoming alerts, correlates operational signals, derives a probable diagnosis, and can optionally use an LLM to refine the final response without replacing deterministic reasoning.

---

## Table of contents

- [Overview](#overview)
- [Why this project exists](#why-this-project-exists)
- [Current capabilities](#current-capabilities)
- [Design principles](#design-principles)
- [Architecture overview](#architecture-overview)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [API endpoints](#api-endpoints)
  - [`GET /health`](#get-health)
  - [`POST /alerts`](#post-alerts)
  - [`POST /postmortems/draft`](#post-postmortemsdraft)
- [Request examples](#request-examples)
- [Response highlights](#response-highlights)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [LLM behavior](#llm-behavior)
- [Testing](#testing)
- [Current status](#current-status)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

`sreagent` is an API-first incident analysis service that receives alerts, gathers structured context, applies deterministic correlation rules, infers a probable diagnosis, and produces outputs that can support triage, escalation, and postmortem drafting.

The project is intentionally designed with a **deterministic-first** architecture. An LLM can be enabled as an **optional refinement layer**, but it does not replace evidence collection or the base reasoning workflow.

This makes the system easier to trust, test, and evolve.

---

## Why this project exists

During incident response, engineers often need to answer the same questions very quickly:

- What is failing?
- Which service or component is most likely affected?
- What evidence supports that conclusion?
- What should the on-call engineer inspect next?
- Can we start a postmortem draft from the alert itself?

`sreagent` aims to standardize that first-response layer with a pipeline that is:

- safe
- structured
- explainable
- easy to extend
- usable locally without external dependencies

---

## Current capabilities

- Accept incident alerts through an HTTP API
- Normalize and enrich incoming alert context
- Collect evidence from Prometheus and application logs in Loki
- Apply deterministic correlation rules
- Infer probable component, failure type, and scope
- Return evidence-backed hypotheses with confidence values
- Generate a draft postmortem using the same incident analysis pipeline
- Optionally refine the final response with an LLM
- Run in read-only mode with safe local defaults
- Fall back to a mock LLM provider when the real provider is disabled or unavailable

---

## Design principles

### Deterministic first

Correlation rules are the primary reasoning layer. The system should produce useful output even when no LLM is enabled.

### LLM as advisory only

The LLM can improve summarization and refine hypotheses, but it must not invent evidence or replace deterministic signals.

### Read-only by default

The project does not mutate external systems. It is designed as an analysis assistant, not an actuator.

### Secrets stay local

Bot tokens, API keys, and demo-specific chat IDs should be injected through environment variables or local secret files under `deploy/secrets/`, never committed to the repository.

### Safe fallback behavior

The application still runs locally without real external credentials. When the LLM is misconfigured or unavailable, the system falls back safely to a mock provider.

### Evidence-backed output

Conclusions are tied to structured evidence and `evidence_ids`, making the response easier to inspect and validate.

---

## Architecture overview

The analysis pipeline follows this flow:

1. **Alert intake**
2. **Normalization**
3. **Enrichment**
4. **Deterministic correlation**
5. **Diagnosis inference**
6. **Optional LLM refinement**
7. **Final summarization**

### High-level flow

```text
Alert Input
   ↓
Normalization
   ↓
Enrichment (Prometheus + logs da aplicação no Loki + contexto de workload)
   ↓
Deterministic Correlation Rules
   ↓
Probable Diagnosis
   ↓
Optional LLM Refinement
   ↓
Structured Incident Response
```

### Current provider model

The project is structured so integrations can be swapped later for real adapters.  
At the moment, the local demo already supports **read-only HTTP integration** with:

- Prometheus
- Loki

Kubernetes and Slack remain lightweight adapters, which keeps the application easy to run locally while preserving a clean path to real integrations later.

---

## Tech stack

- **Python 3.11+**
- **FastAPI**
- **Pydantic**
- **Uvicorn**
- **Pytest**
- **OpenAI Python client** (optional LLM provider)

---

## Project structure

```text
sreagent/
├── app/
│   ├── api/
│   ├── ai/
│   ├── core/
│   ├── models/
│   ├── providers/
│   ├── services/
│   ├── dependencies.py
│   └── main.py
├── tests/
├── pyproject.toml
└── README.md
```

### Structure summary

- `app/api/` → FastAPI route handlers
- `app/ai/` → LLM abstractions, providers, and related logic
- `app/core/` → config and shared core definitions
- `app/models/` → request and response schemas
- `app/providers/` → mock external system adapters
- `app/services/` → enrichment, correlation, diagnosis, and orchestration logic
- `tests/` → automated test coverage

---

## API endpoints

### `GET /health`

Basic healthcheck endpoint.

#### Example response

```json
{
  "status": "ok"
}
```

---

### `POST /alerts`

Receives an alert payload, runs the incident analysis pipeline, and returns a structured incident assessment.

The response can include:

- normalized alert data
- collected evidence
- correlation result
- probable diagnosis
- hypotheses
- optional LLM refinement
- notification preview

---

### `POST /postmortems/draft`

Generates a draft postmortem using the same incident analysis pipeline used by `/alerts`.

This endpoint is intended to turn the original alert and a basic timeline into a structured draft that can later be improved by humans.

---

## Request examples

### Example alert request

```bash
curl -X POST http://127.0.0.1:8000/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Token: change-me" \
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

If you do not configure `SREAGENT_API_TOKEN`, remove the `X-API-Token` header.

---

### Example postmortem draft request

```bash
curl -X POST http://127.0.0.1:8000/postmortems/draft \
  -H "Content-Type: application/json" \
  -H "X-API-Token: change-me" \
  -d '{
    "alert": {
      "source": "grafana",
      "severity": "critical",
      "message": "Checkout latency is above threshold.",
      "labels": {
        "service": "checkout",
        "environment": "prod"
      }
    },
    "timeline": [
      {
        "timestamp": "2026-04-22T10:15:00Z",
        "phase": "detected",
        "summary": "Pager notified the on-call engineer.",
        "source": "pagerduty"
      }
    ]
  }'
```

---

## Response highlights

A typical `/alerts` response can include the following logical sections:

- **Normalized alert**
- **Structured evidence**
- **Detected signals**
- **Correlation rule**
- **Confidence**
- **Diagnosis**
- **Hypotheses**
- **Optional `llm_analysis`**
- **Notification preview**

### Example conceptual shape

```json
{
  "alert": {
    "source": "grafana",
    "severity": "critical",
    "message": "Checkout latency is above threshold.",
    "labels": {
      "service": "checkout",
      "environment": "prod"
    }
  },
  "signals": [
    "recent deploy detected",
    "dominant error detected",
    "restart detected"
  ],
  "correlation": {
    "rule": "restart-detected",
    "confidence": 0.82
  },
  "diagnosis": {
    "probable_component": "checkout",
    "probable_failure_type": "runtime instability",
    "probable_scope": "service-level",
    "confidence": 0.82,
    "supporting_evidence_ids": [
      "kubernetes-workload-status"
    ]
  },
  "hypotheses": [
    {
      "title": "The checkout workload is unstable after a recent change.",
      "confidence": 0.82,
      "evidence_ids": [
        "kubernetes-workload-status",
        "deployment-history"
      ]
    }
  ],
  "llm_analysis": {
    "summary": "Optional refinement based on deterministic findings."
  }
}
```

---

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/luanfellp/sreagent.git
cd sreagent
```

### 2. Create and activate a virtual environment

#### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -e .[dev]
```

### 4. Demo stack secrets and local env

For the local demo stack, keep secrets out of Git:

```bash
cp deploy/.env.example deploy/.env
mkdir -p deploy/secrets
printf 'your-telegram-bot-token' > deploy/secrets/telegram_bot_token.txt
```

If you do not want Telegram delivery, leave `SREAGENT_TELEGRAM_CHAT_ID` empty in `deploy/.env` and skip the token file.

---

## Running locally

Start the API with:

```bash
uvicorn app.main:app --reload
```

The application should be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive docs should be available at:

```text
http://127.0.0.1:8000/docs
```

---

## Configuration

All environment variables are optional unless you want to:

- protect the alert endpoint with a token
- enable the OpenAI-backed LLM provider

### Example configuration

```bash
export SREAGENT_API_TOKEN="change-me"
export SREAGENT_READ_ONLY_MODE=true
export SREAGENT_ENABLE_LLM=false
export SREAGENT_LLM_PROVIDER=openai
export SREAGENT_OPENAI_API_KEY=""
export SREAGENT_OPENAI_MODEL=gpt-5
export SREAGENT_LLM_TIMEOUT_SECONDS=15
```

### Environment variables

| Variable | Description | Default |
|---|---|---|
| `SREAGENT_API_TOKEN` | Optional API token required by `POST /alerts` when set | unset |
| `SREAGENT_READ_ONLY_MODE` | Keeps the application in read-only posture | `true` |
| `SREAGENT_ENABLE_LLM` | Enables the LLM refinement layer | `false` |
| `SREAGENT_LLM_PROVIDER` | LLM provider identifier | `openai` |
| `SREAGENT_OPENAI_API_KEY` | OpenAI API key | unset |
| `SREAGENT_OPENAI_MODEL` | OpenAI model name | `gpt-5` |
| `SREAGENT_LLM_TIMEOUT_SECONDS` | Timeout for LLM requests | `15` |

---

## LLM behavior

The project supports an optional LLM analysis layer after deterministic correlation.

### Pipeline behavior

- alert input
- enrichment
- correlation
- optional LLM analysis
- final summarization

### Important constraints

- the system remains read-only
- deterministic correlation remains the base layer
- the LLM is advisory and should not replace collected evidence
- if the LLM is disabled or unavailable, the system falls back safely
- common sensitive values are redacted before sending context to the LLM

### Provider behavior

- `SREAGENT_ENABLE_LLM=false` → use mock provider
- `SREAGENT_ENABLE_LLM=true` and missing API key → use mock provider with safe fallback
- `SREAGENT_ENABLE_LLM=true` and valid configuration → use the OpenAI provider

---

## Testing

Run the test suite with:

```bash
pytest
```

You can also run in verbose mode:

```bash
pytest -v
```

---

## Current status

This project is currently an **MVP / local-first API skeleton** focused on:

- incident intake
- deterministic correlation
- diagnosis shaping
- análise inicial apoiada por métricas + logs reais da aplicação
- safe optional LLM refinement
- draft postmortem generation

The current integrations are mocked, which keeps the system easy to run and test locally.

---

## Roadmap

Possible next steps for the project:

- [ ] Add richer multi-service log correlation
- [ ] Add real Kubernetes integration
- [ ] Improve correlation coverage and confidence scoring
- [ ] Store incident history
- [ ] Add Slack or PagerDuty outbound integrations
- [ ] Add CI pipeline
- [ ] Add Docker support
- [ ] Add deployment manifests
- [ ] Add authentication and rate limiting improvements

---

## License

MIT

---

## Notes

This project is intentionally designed around a simple principle:

> collect evidence first, correlate deterministically, and use AI only to refine the final response.

That makes `sreagent` easier to test, reason about, and trust during incident response.

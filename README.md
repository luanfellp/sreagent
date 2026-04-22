# sreagent
<<<<<<< HEAD

SRE incident copilot built with Python and FastAPI.

## Goal
Receive incident alerts, enrich context, correlate signals, optionally refine the assessment with an LLM, and generate structured outputs for on-call engineers and postmortem drafting.

## Scope v1
- HTTP alert intake
- Structured incident summary
- Deterministic correlation rules
- Probable component and failure diagnosis
- Draft postmortem generation
- Mocked integrations
- Read-only mode

## Stack
- Python
- FastAPI
- Pytest

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Configuration
Environment variables are optional unless you want to protect the alert endpoint.

```bash
export SREAGENT_API_TOKEN="change-me"
export SREAGENT_READ_ONLY_MODE=true
export SREAGENT_ENABLE_LLM=false
export SREAGENT_LLM_PROVIDER=openai
export SREAGENT_OPENAI_API_KEY=""
export SREAGENT_OPENAI_MODEL=gpt-5
export SREAGENT_LLM_TIMEOUT_SECONDS=15
```

When `SREAGENT_API_TOKEN` is set, `POST /alerts` requires the header `X-API-Token`.

## Optional LLM layer
The project now supports an optional LLM analysis layer after deterministic correlation.

Pipeline:

- alert input
- enrichment
- correlation
- optional LLM analysis
- final summarization

Important constraints:

- the system remains read-only
- deterministic correlation remains the base layer
- the LLM is advisory and cannot replace collected evidence
- if the LLM is disabled or unavailable, the system falls back to a mock provider
- the system redacts common sensitive values before sending context to the LLM

### Provider behavior
- `SREAGENT_ENABLE_LLM=false`: use mock provider
- `SREAGENT_ENABLE_LLM=true` and missing `SREAGENT_OPENAI_API_KEY`: use mock provider with safe fallback
- `SREAGENT_ENABLE_LLM=true` and valid OpenAI config: use the OpenAI provider

### Example `.env`
```bash
SREAGENT_API_TOKEN=change-me
SREAGENT_READ_ONLY_MODE=true
SREAGENT_ENABLE_LLM=true
SREAGENT_LLM_PROVIDER=openai
SREAGENT_OPENAI_API_KEY=sk-example
SREAGENT_OPENAI_MODEL=gpt-5
SREAGENT_LLM_TIMEOUT_SECONDS=15
```

## Run
```bash
uvicorn app.main:app --reload
```

## Test
```bash
pytest
```

## Example request
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

If you did not configure `SREAGENT_API_TOKEN`, remove the `X-API-Token` header.

## Example postmortem draft request
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

## Response shape
`POST /alerts` returns a read-only incident assessment with:

- normalized alert data
- structured evidence from Prometheus, Loki, and Kubernetes mocks
- deterministic signals such as recent deploy, dominant error, restart, and crashloop
- correlation rule, confidence, and evidence-backed hypotheses
- explicit diagnosis fields for probable component, failure type, and scope
- optional LLM-backed refinement with structured output and safe fallback to mock
- notification preview for Slack

Additional response block:

- `diagnosis`
  - `probable_component`
  - `probable_failure_type`
  - `probable_scope`
  - `confidence`
  - `supporting_evidence_ids`

Example `llm_analysis` block:

```json
{
  "summary": "Deterministic correlation points to rule crashloop-detected for service checkout in prod.",
  "hypotheses_refined": [
    {
      "title": "The workload for checkout is crash looping and unstable.",
      "confidence": 0.85,
      "evidence_ids": ["kubernetes-workload-status"],
      "rationale": "This refinement mirrors the deterministic correlation and does not add new facts beyond the collected evidence."
    }
  ],
  "next_steps": [
    "Inspect restart reasons and pod events for the failing workload.",
    "Validate the correlated signals against dashboards and logs."
  ],
  "confidence_notes": [
    "Mock LLM provider in use; output is a deterministic refinement layer."
  ]
}
```

## Architecture notes
- FastAPI dependencies are used to inject providers, which makes it easier to swap mocks for real APIs later.
- External systems are represented by typed interfaces and mock adapters.
- Correlation remains deterministic and is still the primary reasoning layer.
- A unified incident context is built after enrichment, correlation, diagnosis, and LLM analysis.
- The LLM receives only structured context: normalized alert, signals, correlation output, summarized evidence, and deterministic hypotheses.
- The OpenAI integration is isolated in its own provider and uses a mock fallback when disabled, misconfigured, or unavailable.
- The system validates LLM `evidence_ids` before returning the final response.
- The postmortem draft endpoint reuses the same incident analysis pipeline.
- Structured log events are emitted for correlation, LLM completion/fallback, and postmortem draft creation.
- Common sensitive values such as emails, IPs, and token-like strings are redacted before sending context to the LLM and when drafting timeline text for postmortems.

## Current behavior
- `GET /health` returns API health status.
- `POST /alerts` normalizes the payload, gathers structured mock evidence, applies deterministic correlation rules, derives a probable diagnosis, optionally refines the result with an LLM provider, and returns a structured JSON response.
- `POST /postmortems/draft` generates a read-only deterministic draft postmortem using the same incident analysis pipeline.
- Prometheus, Loki, Kubernetes, and Slack are represented by read-only mock interfaces only.
- The project still runs locally without any external credentials because the LLM layer safely falls back to mock behavior.
=======
SRE AI Agent
>>>>>>> f6fbd2622345eea046f8b40baf5d69bade276af8

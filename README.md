# sreagent

SRE incident copilot built with Python and FastAPI.

`sreagent` is a read-only incident analysis API designed to help on-call and platform teams turn alerts into structured, evidence-backed incident assessments. It enriches incoming alerts, correlates operational signals, derives a probable diagnosis, and can optionally use an LLM to refine the response without replacing deterministic reasoning.

## Why this project exists

During incident response, engineers often need to answer the same questions quickly:

- What is failing?
- Which service or component is most likely affected?
- What evidence supports that conclusion?
- What should the on-call engineer check next?
- Can we draft a postmortem starting from the alert itself?

`sreagent` aims to standardize that first response layer with a pipeline that is safe, explainable, and easy to evolve.

## Current capabilities

- Accept alerts through an HTTP API
- Normalize and enrich alert context
- Correlate deterministic operational signals
- Produce a structured incident summary
- Infer a probable component, failure type, and scope
- Generate a draft postmortem from the same incident pipeline
- Optionally refine the analysis with an LLM
- Preserve a read-only posture with mocked provider integrations

## Design principles

- **Deterministic first**: correlation rules are the primary reasoning layer
- **LLM as advisory only**: the model can refine wording and hypotheses, but should not invent evidence
- **Read-only by default**: integrations do not mutate external systems
- **Safe fallback behavior**: the application still runs locally without external credentials
- **Evidence-backed output**: the response is structured around collected signals and supporting evidence IDs

## Architecture overview

The analysis pipeline follows this flow:

1. **Alert intake**
2. **Enrichment**
3. **Correlation**
4. **Diagnosis**
5. **Optional LLM refinement**
6. **Final summarization**

The current implementation is structured so external systems can be swapped later for real adapters. For now, Prometheus, Loki, Kubernetes, and Slack are represented through read-only mock integrations.

## API

### `GET /health`

Basic healthcheck endpoint.

**Response**
```json
{
  "status": "ok"
}

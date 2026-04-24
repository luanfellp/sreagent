# SREAgent Review

## Current state

SREAgent is already a credible MVP for a public SRE demo.

Strong points:

- clean FastAPI service boundary
- read-only posture enforced at startup
- deterministic evidence collection before LLM refinement
- real Prometheus and Loki integration in the local demo
- grouped Alertmanager payload handling
- structured tests for API, correlation, sanitization, and guardrails

## What was strengthened

- repository hygiene and packaging exclusions for local secrets and machine-local artifacts
- dedicated Telegram notification modules with background delivery
- grouped Alertmanager webhook processing with explicit `firing` / `resolved` handling
- safer Prometheus and Loki label construction
- evidence scoring correlation with primary hypothesis, secondary signals, and information gaps
- CI and lint readiness with Ruff + pytest

## Remaining limitations

- Kubernetes evidence is still mock-backed
- correlation is intentionally conservative and does not claim root cause certainty
- Zabbix is present in the demo but not queried by the API
- Telegram is still a simple delivery channel rather than a durable notification pipeline

## Recommended next iterations

1. Add a real Kubernetes read-only provider.
2. Introduce richer correlation signals for downstream dependency failures.
3. Add screenshots and a short GIF for the public portfolio narrative.
4. Add a small dashboard or endpoint showing recent grouped webhook processing stats.

from dataclasses import dataclass

from app.domain.models import (
    CorrelationDetails,
    CorrelationOutcome,
    EnrichedAlert,
    Hypothesis,
)


@dataclass(frozen=True)
class _HypothesisCandidate:
    kind: str
    statement: str
    score: int
    evidence_ids: list[str]
    supporting_signals: list[str]


def _find_evidence_ids(alert: EnrichedAlert, source: str) -> list[str]:
    return [item.id for item in alert.evidence if item.source == source]


def _confidence_from_score(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _signal_descriptions(alert: EnrichedAlert) -> tuple[list[str], list[str]]:
    secondary_signals: list[str] = []
    information_gaps: list[str] = []

    if alert.signals.recent_deploy:
        secondary_signals.append("deploy recente detectado")
    if alert.signals.high_error_rate:
        secondary_signals.append("taxa de erro elevada no Prometheus")
    if alert.signals.latency_elevated:
        secondary_signals.append("latência p95 elevada")
    if alert.signals.restart_detected:
        secondary_signals.append("restarts recentes no workload")
    if alert.signals.dominant_error:
        secondary_signals.append(
            f"padrão dominante de erro em logs: {alert.signals.dominant_error}"
        )

    if not alert.signals.relevant_logs_found:
        information_gaps.append("Loki não retornou logs relevantes recentes.")
    if alert.alert.environment == "unknown":
        information_gaps.append("O alerta não informou environment de forma confiável.")
    if not _find_evidence_ids(alert, "kubernetes"):
        information_gaps.append("Não há evidência de workload disponível do Kubernetes.")

    return secondary_signals, information_gaps


def _build_candidates(alert: EnrichedAlert) -> list[_HypothesisCandidate]:
    kubernetes_evidence = _find_evidence_ids(alert, "kubernetes")
    loki_evidence = _find_evidence_ids(alert, "loki")
    prometheus_evidence = _find_evidence_ids(alert, "prometheus")
    severity = alert.alert.severity.lower()

    candidates: list[_HypothesisCandidate] = []
    if alert.signals.crashloop_detected:
        candidates.append(
            _HypothesisCandidate(
                kind="crashloop-detected",
                statement=(
                    f"O workload de {alert.alert.service} está em crash loop e é a hipótese principal."
                ),
                score=90 if severity == "critical" else 82,
                evidence_ids=kubernetes_evidence,
                supporting_signals=["crashloop", "restarts"],
            )
        )

    if alert.signals.restart_detected:
        candidates.append(
            _HypothesisCandidate(
                kind="restart-detected",
                statement=(
                    f"O workload de {alert.alert.service} apresenta reinícios recentes e instabilidade."
                ),
                score=60 + (10 if alert.signals.recent_deploy else 0),
                evidence_ids=kubernetes_evidence,
                supporting_signals=["restarts"],
            )
        )

    if alert.signals.recent_deploy:
        candidates.append(
            _HypothesisCandidate(
                kind="recent-deploy-regression",
                statement=(
                    f"Um deploy recente é um forte candidato para a regressão em {alert.alert.service}."
                ),
                score=55
                + (10 if alert.signals.high_error_rate else 0)
                + (10 if alert.signals.latency_elevated else 0)
                + (5 if alert.signals.dominant_error else 0),
                evidence_ids=kubernetes_evidence + prometheus_evidence,
                supporting_signals=["recent_deploy"],
            )
        )

    if alert.signals.dominant_error == "timeout":
        candidates.append(
            _HypothesisCandidate(
                kind="timeout-pattern",
                statement=(
                    f"Os logs indicam timeout como modo de falha dominante em {alert.alert.service}."
                ),
                score=72
                + (8 if alert.signals.latency_elevated else 0)
                + (5 if alert.signals.high_error_rate else 0),
                evidence_ids=loki_evidence + prometheus_evidence,
                supporting_signals=["timeout_logs", "latency"],
            )
        )
    elif alert.signals.dominant_error == "http-5xx":
        candidates.append(
            _HypothesisCandidate(
                kind="http-5xx-spike",
                statement=(
                    f"Há um pico de 5xx sustentado por métricas e logs em {alert.alert.service}."
                ),
                score=74 + (8 if alert.signals.high_error_rate else 0),
                evidence_ids=loki_evidence + prometheus_evidence,
                supporting_signals=["5xx", "error_rate"],
            )
        )
    elif alert.signals.dominant_error:
        candidates.append(
            _HypothesisCandidate(
                kind="dominant-error-detected",
                statement=(
                    f"Os logs apontam {alert.signals.dominant_error} como falha imediata mais provável."
                ),
                score=68,
                evidence_ids=loki_evidence,
                supporting_signals=["dominant_error"],
            )
        )

    candidates.append(
        _HypothesisCandidate(
            kind="service-degradation",
            statement=(
                f"O incidente sugere degradação de serviço em {alert.alert.service} no ambiente {alert.alert.environment}."
            ),
            score=(40 if severity in {"critical", "high"} else 25)
            + (12 if alert.signals.high_error_rate else 0)
            + (10 if alert.signals.latency_elevated else 0),
            evidence_ids=prometheus_evidence + loki_evidence + kubernetes_evidence,
            supporting_signals=["severity", "service_health"],
        )
    )
    return candidates


def correlate_alert(alert: EnrichedAlert) -> CorrelationOutcome:
    severity = alert.alert.severity.lower()
    dedup_key = f"{alert.alert.service}:{alert.alert.environment}:{severity}"
    candidates = sorted(
        _build_candidates(alert),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    primary_candidate = candidates[0]
    primary_confidence = _confidence_from_score(primary_candidate.score)
    hypotheses = [
        Hypothesis(
            kind=candidate.kind,
            statement=candidate.statement,
            confidence=_confidence_from_score(candidate.score),
            score=candidate.score,
            evidence_ids=candidate.evidence_ids,
            supporting_signals=candidate.supporting_signals,
        )
        for candidate in candidates
    ]
    secondary_signals, information_gaps = _signal_descriptions(alert)
    return CorrelationOutcome(
        correlation=CorrelationDetails(
            dedup_key=dedup_key,
            rule=primary_candidate.kind,
            confidence=primary_confidence,
            primary_hypothesis=primary_candidate.statement,
            supporting_evidence_ids=primary_candidate.evidence_ids,
            secondary_signals=secondary_signals,
            information_gaps=information_gaps,
        ),
        hypotheses=hypotheses,
    )

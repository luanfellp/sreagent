from app.domain.models import (
    CorrelationDetails,
    CorrelationOutcome,
    EnrichedAlert,
    Hypothesis,
)


def _confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}[value]


def _find_evidence_ids(alert: EnrichedAlert, source: str) -> list[str]:
    return [item.id for item in alert.evidence if item.source == source]


def correlate_alert(alert: EnrichedAlert) -> CorrelationOutcome:
    severity = alert.alert.severity.lower()
    dedup_key = f"{alert.alert.service}:{alert.alert.environment}:{severity}"
    hypotheses: list[Hypothesis] = []
    rule = "service-alert"

    if alert.signals.recent_deploy:
        rule = "recent-deploy-detected"
        hypotheses.append(
            Hypothesis(
                statement=(
                    f"A recent deploy likely introduced the issue in {alert.alert.service}."
                ),
                confidence="high" if severity == "critical" else "medium",
                evidence_ids=_find_evidence_ids(alert, "kubernetes"),
            )
        )

    if alert.signals.dominant_error:
        rule = "dominant-error-detected"
        hypotheses.append(
            Hypothesis(
                statement=(
                    f"The dominant error pattern is {alert.signals.dominant_error}, "
                    "which is the most likely immediate failure mode."
                ),
                confidence="high",
                evidence_ids=_find_evidence_ids(alert, "loki"),
            )
        )

    if alert.signals.crashloop_detected:
        rule = "crashloop-detected"
        hypotheses.append(
            Hypothesis(
                statement=(
                    f"The workload for {alert.alert.service} is crash looping and unstable."
                ),
                confidence="high",
                evidence_ids=_find_evidence_ids(alert, "kubernetes"),
            )
        )
    elif alert.signals.restart_detected:
        rule = "restart-detected"
        hypotheses.append(
            Hypothesis(
                statement=(
                    f"Recent container restarts suggest instability in {alert.alert.service}."
                ),
                confidence="medium",
                evidence_ids=_find_evidence_ids(alert, "kubernetes"),
            )
        )

    if not hypotheses:
        if severity == "critical":
            rule = "critical-service-alert"
        hypotheses.append(
            Hypothesis(
                statement=(
                    f"The incident is likely centered on service {alert.alert.service} "
                    f"in environment {alert.alert.environment}."
                ),
                confidence="medium" if severity in {"critical", "high"} else "low",
                evidence_ids=[item.id for item in alert.evidence],
            )
        )

    confidence = max(
        hypotheses, key=lambda item: _confidence_rank(item.confidence)
    ).confidence
    return CorrelationOutcome(
        correlation=CorrelationDetails(
            dedup_key=dedup_key,
            rule=rule,
            confidence=confidence,
        ),
        hypotheses=hypotheses,
    )

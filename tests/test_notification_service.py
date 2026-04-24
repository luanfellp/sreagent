from fastapi import BackgroundTasks

from app.domain.llm_models import LLMAnalysisResult
from app.domain.models import (
    AlertResponse,
    CorrelationDetails,
    EnrichmentSignals,
    IncidentDiagnosis,
    NormalizedAlert,
    NotificationPreview,
)
from app.services.notification_service import NotificationService


class _FakeNotifier:
    def __init__(self, enabled: bool):
        self.is_enabled = enabled
        self.calls: list[str] = []

    def send_text(self, text: str) -> bool:
        self.calls.append(text)
        return True


def _alert_response() -> AlertResponse:
    return AlertResponse(
        mode="read-only",
        status="analyzed",
        title="Incidente",
        alert=NormalizedAlert(
            source="grafana",
            severity="critical",
            message="Teste",
            service="checkout",
            environment="prod",
            labels={},
        ),
        signals=EnrichmentSignals(),
        correlation=CorrelationDetails(
            dedup_key="checkout:prod:critical",
            rule="service-degradation",
            confidence="medium",
            primary_hypothesis="Hipótese principal",
            supporting_evidence_ids=[],
            secondary_signals=[],
            information_gaps=[],
        ),
        evidence=[],
        hypotheses=[],
        diagnosis=IncidentDiagnosis(
            probable_component="checkout",
            probable_failure_type="service-degradation",
            probable_scope="single-service",
            confidence="medium",
            supporting_evidence_ids=[],
        ),
        llm_analysis=LLMAnalysisResult(
            summary="Resumo",
            hypotheses_refined=[],
            next_steps=[],
            confidence_notes=[],
        ),
        actions=[],
        non_executed_actions=[],
        notifications=[NotificationPreview(channel="telegram", message="mensagem")],
    )


def test_notification_service_skips_when_telegram_disabled() -> None:
    notifier = _FakeNotifier(enabled=False)
    service = NotificationService(notifier)  # type: ignore[arg-type]
    background_tasks = BackgroundTasks()

    service.schedule_alert_delivery(
        background_tasks,
        source="grafana",
        labels={},
        result=_alert_response(),
    )

    assert background_tasks.tasks == []
    assert notifier.calls == []


def test_notification_service_skips_telegram_feedback_loop() -> None:
    notifier = _FakeNotifier(enabled=True)
    service = NotificationService(notifier)  # type: ignore[arg-type]
    background_tasks = BackgroundTasks()

    service.schedule_alert_delivery(
        background_tasks,
        source="alertmanager",
        labels={"alertname": "TelegramSendFailure"},
        result=_alert_response(),
    )

    assert background_tasks.tasks == []

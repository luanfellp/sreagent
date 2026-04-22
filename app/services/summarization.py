from app.domain.incident_models import IncidentContext
from app.domain.models import AlertResponse, NotificationPreview
from app.integrations.interfaces import SlackClient
from app.integrations.mocks import mock_slack


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def summarize_alert(
    incident: IncidentContext,
    slack_client: SlackClient = mock_slack,
) -> AlertResponse:
    title = (
        f"{incident.alert.severity.upper()} incident alert for {incident.alert.service}"
    )
    status = "analyzed" if incident.alert.severity.lower() != "info" else "observed"
    summary = (
        f"{incident.llm_analysis.summary} | service={incident.alert.service} "
        f"| environment={incident.alert.environment} "
        f"| dedup_key={incident.correlation.dedup_key}"
    )
    actions = [
        "Validate the alert against dashboards and logs before any remediation.",
        "Review the affected workload state and recent deploy history.",
    ]
    if incident.signals.crashloop_detected:
        actions.insert(
            0, "Inspect pod events and restart reasons for the affected workload."
        )
    elif incident.signals.recent_deploy:
        actions.insert(0, "Review the most recent deployment and its rollout timeline.")

    actions = _ordered_unique(actions + incident.llm_analysis.next_steps)

    notification = slack_client.build_notification_preview(title, summary)
    return AlertResponse(
        mode="read-only",
        status=status,
        title=title,
        alert=incident.alert,
        signals=incident.signals,
        correlation=incident.correlation,
        evidence=incident.evidence,
        hypotheses=incident.hypotheses,
        diagnosis=incident.diagnosis,
        llm_analysis=incident.llm_analysis,
        actions=actions,
        notifications=[
            NotificationPreview(
                channel=notification.channel,
                message=notification.message,
            )
        ],
    )

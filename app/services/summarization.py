from app.domain.incident_models import IncidentContext
from app.domain.models import AlertResponse, NotificationPreview
from app.integrations.interfaces import SlackClient
from app.integrations.mocks import mock_slack

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}

STATUS_LABEL = {
    "critical": "Crítico",
    "high": "Alto",
    "medium": "Médio",
    "low": "Baixo",
    "info": "Informativo",
}

CONFIDENCE_LABEL = {
    "high": "Alta",
    "medium": "Média",
    "low": "Baixa",
}

FAILURE_TYPE_LABEL = {
    "service-degradation": "degradação de serviço",
    "crashloop": "crashloop",
    "restart-instability": "instabilidade por restarts",
    "recent-deploy-regression": "possível regressão após deploy",
    "timeout": "timeouts",
    "http-5xx": "pico de erros HTTP 5xx",
    "resolved": "alerta resolvido",
    "unknown": "indefinida",
}

SCOPE_LABEL = {
    "single-service": "serviço único",
    "single-workload": "workload específico",
    "unknown": "escopo indefinido",
}


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
    non_executed_actions: list[str] | None = None,
) -> AlertResponse:
    severity = incident.alert.severity.lower()
    emoji = SEVERITY_EMOJI.get(severity, "⚠️")
    severity_label = STATUS_LABEL.get(severity, severity.title())
    confidence_label = CONFIDENCE_LABEL.get(
        incident.diagnosis.confidence.lower(), incident.diagnosis.confidence
    )
    failure_label = FAILURE_TYPE_LABEL.get(
        incident.diagnosis.probable_failure_type,
        incident.diagnosis.probable_failure_type,
    )
    scope_label = SCOPE_LABEL.get(
        incident.diagnosis.probable_scope,
        incident.diagnosis.probable_scope,
    )

    title = f"{emoji} Incidente {severity_label} em {incident.alert.service}"
    status = "analyzed" if severity != "info" else "observed"

    actions = [
        "✅ Validar o alerta em dashboards e logs antes de qualquer ação.",
        "🛠️ Revisar o estado do workload afetado e o histórico recente de deploys.",
    ]
    if incident.signals.crashloop_detected:
        actions.insert(
            0, "🚨 Inspecionar eventos do pod e motivos de restart do workload afetado."
        )
    elif incident.signals.recent_deploy:
        actions.insert(0, "🚀 Revisar o deploy mais recente e a linha do tempo do rollout.")

    actions = _ordered_unique(actions + incident.llm_analysis.next_steps)
    non_executed_actions = _ordered_unique(
        non_executed_actions
        or [
            "Nenhuma remediação automatizada foi executada pelo SREAgent; o sistema permanece somente leitura.",
        ]
    )

    loki_evidence = next(
        (item for item in incident.evidence if item.source == "loki"), None
    )
    logs_line = (
        loki_evidence.summary if loki_evidence else "Sem evidência recente de logs da aplicação."
    )

    executive_lines = [
        title,
        "",
        f"🧠 Resumo: {incident.llm_analysis.summary}",
        f"🎯 Hipótese principal: {incident.correlation.primary_hypothesis}",
        f"🪵 Logs da aplicação: {logs_line}",
        f"📚 Evidências principais: {', '.join(incident.correlation.supporting_evidence_ids) or 'nenhuma'}",
        f"🎯 Diagnóstico: {failure_label} em {incident.diagnosis.probable_component}",
        f"📈 Confiança: {confidence_label}",
        f"🌍 Ambiente: {incident.alert.environment}",
        f"🧭 Escopo: {scope_label}",
        f"🧩 Regra: {incident.correlation.rule}",
        f"🆔 Dedup: {incident.correlation.dedup_key}",
        f"🔎 Sinais secundários: {', '.join(incident.correlation.secondary_signals) or 'nenhum'}",
        f"❓ Lacunas: {', '.join(incident.correlation.information_gaps) or 'nenhuma'}",
        f"⛔ Ações não executadas: {', '.join(non_executed_actions)}",
        "",
        "➡️ Próximos passos:",
        *[f"• {item}" for item in actions[:3]],
    ]
    summary = "\n".join(executive_lines)

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
        non_executed_actions=non_executed_actions,
        notifications=[
            NotificationPreview(
                channel=notification.channel,
                message=notification.message,
            )
        ],
    )

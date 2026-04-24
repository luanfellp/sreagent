import logging

from app.core.logging_utils import log_event
from app.domain.incident_models import IncidentContext
from app.domain.postmortem_models import (
    PostmortemDraft,
    PostmortemDraftRequest,
    PostmortemTimelineEvent,
)
from app.services.redaction import redact_text

logger = logging.getLogger(__name__)


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def build_postmortem_draft(
    incident: IncidentContext, request: PostmortemDraftRequest
) -> PostmortemDraft:
    title = request.incident_title or (
        f"📝 Rascunho de postmortem para incidente {incident.alert.severity} em {incident.alert.service}"
    )
    timeline = [
        PostmortemTimelineEvent(
            timestamp=item.timestamp,
            phase=item.phase,
            summary=redact_text(item.summary),
            source=item.source,
        )
        for item in request.timeline
    ]
    confirmed_facts = _ordered_unique(
        [
            f"Fonte do alerta: {incident.alert.source} com severidade {incident.alert.severity}.",
            f"Regra principal de correlação: {incident.correlation.rule}.",
            *[redact_text(item.summary) for item in incident.evidence],
        ]
    )
    probable_contributing_factors = _ordered_unique(
        [item.statement for item in incident.hypotheses]
    )
    unknowns = [
        "A causa raiz ainda não está confirmada; a avaliação atual é baseada em evidências, mas ainda provisória.",
    ]
    if not timeline:
        unknowns.append(
            "Uma linha do tempo detalhada do incidente não foi informada na solicitação do postmortem."
        )

    action_items = _ordered_unique(
        [
            *incident.llm_analysis.next_steps,
            "🧾 Documentar a evidência validada da causa raiz antes de encerrar a revisão do incidente.",
        ]
    )
    evidence_references = [item.id for item in incident.evidence]
    impact_summary = (
        f"O alerta indica um problema de severidade {incident.alert.severity} afetando {incident.alert.service} "
        f"em {incident.alert.environment}. O tipo de falha mais provável é "
        f"{incident.diagnosis.probable_failure_type}."
    )
    detection_summary = (
        f"O incidente foi detectado por {incident.alert.source} e correlacionado como "
        f"{incident.correlation.rule}."
    )

    draft = PostmortemDraft(
        mode="read-only",
        status="draft",
        title=title,
        alert=incident.alert,
        diagnosis=incident.diagnosis,
        incident_summary=incident.llm_analysis.summary,
        impact_summary=impact_summary,
        detection_summary=detection_summary,
        timeline=timeline,
        confirmed_facts=confirmed_facts,
        probable_contributing_factors=probable_contributing_factors,
        root_cause_status="hypothesis-only",
        unknowns=unknowns,
        action_items=action_items,
        evidence_references=evidence_references,
        llm_summary=incident.llm_analysis.summary,
    )
    log_event(
        logger,
        logging.INFO,
        "incident.postmortem.draft_created",
        service=incident.alert.service,
        environment=incident.alert.environment,
        correlation_rule=incident.correlation.rule,
    )
    return draft

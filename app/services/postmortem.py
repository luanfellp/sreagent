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
        f"Draft postmortem for {incident.alert.service} {incident.alert.severity} incident"
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
            f"Alert source was {incident.alert.source} with severity {incident.alert.severity}.",
            f"Primary correlation rule was {incident.correlation.rule}.",
            *[redact_text(item.summary) for item in incident.evidence],
        ]
    )
    probable_contributing_factors = _ordered_unique(
        [item.statement for item in incident.hypotheses]
    )
    unknowns = [
        "Root cause remains unconfirmed; the current assessment is evidence-based but provisional.",
    ]
    if not timeline:
        unknowns.append(
            "A detailed incident timeline was not provided in the postmortem draft request."
        )

    action_items = _ordered_unique(
        [
            *incident.llm_analysis.next_steps,
            "Document validated root cause evidence before closing the incident review.",
        ]
    )
    evidence_references = [item.id for item in incident.evidence]
    impact_summary = (
        f"The alert indicates a {incident.alert.severity} issue affecting {incident.alert.service} "
        f"in {incident.alert.environment}. The most likely failure type is "
        f"{incident.diagnosis.probable_failure_type}."
    )
    detection_summary = (
        f"The incident was detected by {incident.alert.source} and correlated as "
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

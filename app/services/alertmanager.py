from dataclasses import dataclass

from app.domain.models import AlertInput

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

SEVERITY_ALIASES = {
    "warning": "medium",
    "warn": "medium",
    "error": "high",
}


@dataclass(frozen=True)
class AlertmanagerGroupInput:
    alert: AlertInput
    status: str
    alert_count: int


def _normalize_severity(value: str | None) -> str:
    normalized = (value or "info").strip().lower()
    return SEVERITY_ALIASES.get(normalized, normalized)


def _shared_mapping(alerts: list[dict], field: str) -> dict[str, str]:
    if not alerts:
        return {}

    first = alerts[0].get(field, {}) or {}
    shared = {key: str(value) for key, value in first.items()}
    for alert in alerts[1:]:
        current = alert.get(field, {}) or {}
        shared = {
            key: value
            for key, value in shared.items()
            if key in current and str(current[key]) == value
        }
    return shared


def _group_key(payload: dict, alert: dict) -> tuple[str, str, str, str, str]:
    common_labels = payload.get("commonLabels") or {}
    labels = alert.get("labels", {}) or {}

    service = str(labels.get("service") or common_labels.get("service") or "unknown")
    environment = str(
        labels.get("environment") or common_labels.get("environment") or "unknown"
    )
    alert_name = str(
        labels.get("alertname") or common_labels.get("alertname") or "unknown-alert"
    )
    severity = _normalize_severity(
        labels.get("severity") or common_labels.get("severity") or "critical"
    )
    status = str(alert.get("status") or payload.get("status") or "firing").strip().lower()
    return service, environment, alert_name, severity, status


def build_grouped_alert_inputs(payload: dict) -> list[AlertmanagerGroupInput]:
    alerts = payload.get("alerts") or [payload]
    grouped: dict[tuple[str, str, str, str, str], list[dict]] = {}
    for alert in alerts:
        key = _group_key(payload, alert)
        grouped.setdefault(key, []).append(alert)

    groups: list[AlertmanagerGroupInput] = []
    for (service, environment, alert_name, severity, status), group_alerts in grouped.items():
        common_labels = payload.get("commonLabels") or {}
        common_annotations = payload.get("commonAnnotations") or {}

        labels = {
            **{
                key: value
                for key, value in common_labels.items()
                if key not in {"service", "environment", "severity"}
            },
            **_shared_mapping(group_alerts, "labels"),
        }
        annotations = {
            **common_annotations,
            **_shared_mapping(group_alerts, "annotations"),
        }

        alert_names = sorted(
            {
                str((alert.get("labels", {}) or {}).get("alertname"))
                for alert in group_alerts
                if (alert.get("labels", {}) or {}).get("alertname")
            }
        )

        labels.update(
            {
                "service": service,
                "environment": environment,
                "alertname": alert_name,
                "severity": severity,
                "alertmanager_status": status,
                "alert_count": str(len(group_alerts)),
            }
        )
        if alert_names:
            labels["alert_names"] = ",".join(alert_names)

        message = (
            annotations.get("summary")
            or annotations.get("description")
            or labels.get("alert_names")
            or labels.get("alertname")
            or "alert"
        )
        if len(group_alerts) > 1:
            message = f"{message} ({len(group_alerts)} alerts grouped by Alertmanager)"

        groups.append(
            AlertmanagerGroupInput(
                alert=AlertInput(
                    source="alertmanager",
                    severity=severity,
                    message=message,
                    labels={key: str(value) for key, value in labels.items()},
                ),
                status=status,
                alert_count=len(group_alerts),
            )
        )

    return sorted(
        groups,
        key=lambda group: (
            group.alert.labels.get("service", "unknown"),
            group.alert.labels.get("environment", "unknown"),
            group.alert.labels.get("alertname", "unknown-alert"),
            -SEVERITY_RANK.get(group.alert.severity, 0),
            group.status,
        ),
    )

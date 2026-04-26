from collections import deque
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from app.domain.history_models import IncidentHistoryRecord
from app.domain.models import AlertResponse


class IncidentStore:
    def __init__(self, max_records: int = 100):
        self._max_records = max_records
        self._records: deque[IncidentHistoryRecord] = deque()
        self._lock = Lock()

    def add(self, result: AlertResponse) -> IncidentHistoryRecord:
        record = IncidentHistoryRecord(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            status=result.status,
            title=result.title,
            severity=result.alert.severity,
            service=result.alert.service,
            environment=result.alert.environment,
            source=result.alert.source,
            dedup_key=result.correlation.dedup_key,
            correlation_rule=result.correlation.rule,
            confidence=result.correlation.confidence,
            primary_hypothesis=result.correlation.primary_hypothesis,
            evidence_ids=result.correlation.supporting_evidence_ids,
            notification_channels=[
                notification.channel for notification in result.notifications
            ],
            result=result,
        )
        with self._lock:
            self._records.appendleft(record)
            while len(self._records) > self._max_records:
                self._records.pop()
        return record

    def list_recent(
        self,
        limit: int = 20,
        service: str | None = None,
        status: str | None = None,
    ) -> list[IncidentHistoryRecord]:
        with self._lock:
            records = list(self._records)

        if service:
            records = [record for record in records if record.service == service]
        if status:
            records = [record for record in records if record.status == status]
        return records[:limit]

    def get(self, incident_id: str) -> IncidentHistoryRecord | None:
        with self._lock:
            for record in self._records:
                if record.id == incident_id:
                    return record
        return None

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_incident_store, require_api_token
from app.domain.history_models import IncidentHistoryRecord, IncidentHistoryResponse
from app.services.incident_store import IncidentStore

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_api_token)],
)


@router.get("/recent", response_model=IncidentHistoryResponse)
def list_recent_incidents(
    store: Annotated[IncidentStore, Depends(get_incident_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    service: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> IncidentHistoryResponse:
    incidents = store.list_recent(
        limit=limit,
        service=service,
        status=status_filter,
    )
    return IncidentHistoryResponse(count=len(incidents), incidents=incidents)


@router.get("/{incident_id}", response_model=IncidentHistoryRecord)
def get_incident(
    incident_id: str,
    store: Annotated[IncidentStore, Depends(get_incident_store)],
) -> IncidentHistoryRecord:
    incident = store.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )
    return incident

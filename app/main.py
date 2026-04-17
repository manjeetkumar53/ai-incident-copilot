from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request

from app.models import (
    ApprovalRequest,
    ApprovalResponse,
    ExecuteRequest,
    ExecuteResponse,
    IncidentDetailResponse,
    IncidentIngestRequest,
    IncidentListResponse,
    IncidentRecord,
    IncidentStatus,
    IntegrationIngestRequest,
    IngestResponse,
    MetricsSummaryResponse,
    PlanResponse,
    TimelineEvent,
)
from app.services.planner import create_plan
from app.services.authz import require_role
from app.services.policy import check_execution_policy
from app.services.store import store

app = FastAPI(title="AI Incident Copilot", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/incidents/ingest", response_model=IngestResponse, status_code=201)
def ingest_incident(payload: IncidentIngestRequest) -> IngestResponse:
    incident_id = str(uuid.uuid4())
    record = IncidentRecord(
        id=incident_id,
        title=payload.title,
        service=payload.service,
        severity=payload.severity,
        source=payload.source,
        summary=payload.summary,
        status=IncidentStatus.open,
    )
    store.add_incident(record)
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="incident.ingested", actor="system", detail=f"Source={payload.source}"),
    )
    return IngestResponse(incident_id=incident_id, status=record.status)


@app.post("/v1/integrations/{source}/ingest", response_model=IngestResponse, status_code=201)
def ingest_from_integration(source: str, payload: IntegrationIngestRequest) -> IngestResponse:
    source = source.strip().lower()
    if source not in {"pagerduty", "slack", "webhook"}:
        raise HTTPException(status_code=400, detail="Unsupported integration source")

    incident_id = str(uuid.uuid4())
    record = IncidentRecord(
        id=incident_id,
        title=payload.title,
        service=payload.service,
        severity=payload.severity,
        source=source,
        summary=payload.summary,
        status=IncidentStatus.open,
    )
    store.add_incident(record)
    detail = f"Source={source} external_id={payload.external_id or 'n/a'}"
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="incident.ingested", actor="integration", detail=detail),
    )
    return IngestResponse(incident_id=incident_id, status=record.status)


@app.post("/v1/incidents/{incident_id}/plan", response_model=PlanResponse)
def plan_incident(incident_id: str) -> PlanResponse:
    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    plan = create_plan(incident)
    store.add_plan(incident_id, plan)
    store.update_incident_status(incident_id, IncidentStatus.planned.value)
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="plan.generated", actor="copilot", detail=f"Runbook={plan.runbook_id}"),
    )
    return PlanResponse(status=IncidentStatus.planned, plan=plan)


@app.post("/v1/incidents/{incident_id}/approve", response_model=ApprovalResponse)
def approve_plan(incident_id: str, payload: ApprovalRequest, request: Request) -> ApprovalResponse:
    require_role(request, {"incident_commander", "engineering_manager"})

    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if store.get_plan(incident_id) is None:
        raise HTTPException(status_code=409, detail="Plan must be generated before approval")

    store.update_incident_status(incident_id, IncidentStatus.approved.value)
    note = payload.comment or "No comment"
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="plan.approved", actor=payload.approved_by, detail=note),
    )
    return ApprovalResponse(status=IncidentStatus.approved, approved_by=payload.approved_by)


@app.post("/v1/incidents/{incident_id}/execute", response_model=ExecuteResponse)
def execute_plan(incident_id: str, payload: ExecuteRequest, request: Request) -> ExecuteResponse:
    role = require_role(request, {"incident_commander", "sre_oncall"})

    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status != IncidentStatus.approved:
        raise HTTPException(status_code=409, detail="Execution requires approved status")

    plan = store.get_plan(incident_id)
    allowed, reason = check_execution_policy(incident, role, plan)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    store.update_incident_status(incident_id, IncidentStatus.executing.value)
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="execution.started", actor=payload.executed_by, detail="Running approved steps"),
    )

    store.update_incident_status(incident_id, IncidentStatus.mitigated.value)
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="incident.mitigated", actor=payload.executed_by, detail="Mitigation marked complete"),
    )
    return ExecuteResponse(
        status=IncidentStatus.mitigated,
        summary="Approved mitigation workflow executed and incident marked as mitigated.",
    )


@app.get("/v1/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str) -> IncidentDetailResponse:
    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentDetailResponse(
        incident=incident,
        plan=store.get_plan(incident_id),
        timeline=store.get_timeline(incident_id),
    )


@app.get("/v1/incidents", response_model=IncidentListResponse)
def list_incidents(
    status: IncidentStatus | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> IncidentListResponse:
    items, total = store.list_incidents(
        status=status.value if status else None,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return IncidentListResponse(items=items, total=total)


@app.get("/v1/metrics/summary", response_model=MetricsSummaryResponse)
def metrics_summary() -> MetricsSummaryResponse:
    return MetricsSummaryResponse(**store.metrics_summary())

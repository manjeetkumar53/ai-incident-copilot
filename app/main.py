from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException

from app.models import (
    ApprovalRequest,
    ApprovalResponse,
    ExecuteRequest,
    ExecuteResponse,
    IncidentDetailResponse,
    IncidentIngestRequest,
    IncidentRecord,
    IncidentStatus,
    IngestResponse,
    PlanResponse,
    TimelineEvent,
)
from app.services.planner import create_plan
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


@app.post("/v1/incidents/{incident_id}/plan", response_model=PlanResponse)
def plan_incident(incident_id: str) -> PlanResponse:
    incident = store.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    plan = create_plan(incident)
    store.add_plan(incident_id, plan)
    incident.status = IncidentStatus.planned
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="plan.generated", actor="copilot", detail=f"Runbook={plan.runbook_id}"),
    )
    return PlanResponse(status=incident.status, plan=plan)


@app.post("/v1/incidents/{incident_id}/approve", response_model=ApprovalResponse)
def approve_plan(incident_id: str, payload: ApprovalRequest) -> ApprovalResponse:
    incident = store.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident_id not in store.plans:
        raise HTTPException(status_code=409, detail="Plan must be generated before approval")

    incident.status = IncidentStatus.approved
    note = payload.comment or "No comment"
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="plan.approved", actor=payload.approved_by, detail=note),
    )
    return ApprovalResponse(status=incident.status, approved_by=payload.approved_by)


@app.post("/v1/incidents/{incident_id}/execute", response_model=ExecuteResponse)
def execute_plan(incident_id: str, payload: ExecuteRequest) -> ExecuteResponse:
    incident = store.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status != IncidentStatus.approved:
        raise HTTPException(status_code=409, detail="Execution requires approved status")

    incident.status = IncidentStatus.executing
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="execution.started", actor=payload.executed_by, detail="Running approved steps"),
    )

    incident.status = IncidentStatus.mitigated
    store.add_timeline_event(
        incident_id,
        TimelineEvent(event="incident.mitigated", actor=payload.executed_by, detail="Mitigation marked complete"),
    )
    return ExecuteResponse(
        status=incident.status,
        summary="Approved mitigation workflow executed and incident marked as mitigated.",
    )


@app.get("/v1/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str) -> IncidentDetailResponse:
    incident = store.incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentDetailResponse(
        incident=incident,
        plan=store.plans.get(incident_id),
        timeline=store.timeline.get(incident_id, []),
    )

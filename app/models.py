from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class IncidentStatus(str, Enum):
    open = "open"
    planned = "planned"
    approved = "approved"
    executing = "executing"
    mitigated = "mitigated"


class StepType(str, Enum):
    read_only = "read_only"
    write_action = "write_action"


class IncidentIngestRequest(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    service: str = Field(min_length=2, max_length=100)
    severity: Severity
    source: Literal["pagerduty", "slack", "webhook"] = "webhook"
    summary: str = Field(min_length=5, max_length=2000)


class IntegrationIngestRequest(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    service: str = Field(min_length=2, max_length=100)
    severity: Severity
    summary: str = Field(min_length=5, max_length=2000)
    external_id: str | None = Field(default=None, max_length=120)


class PlanStep(BaseModel):
    id: str
    description: str
    step_type: StepType


class IncidentPlan(BaseModel):
    incident_id: str
    runbook_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    steps: list[PlanStep]


class ApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=100)
    comment: str | None = Field(default=None, max_length=1000)


class ExecuteRequest(BaseModel):
    executed_by: str = Field(min_length=2, max_length=100)


class IncidentRecord(BaseModel):
    id: str
    title: str
    service: str
    severity: Severity
    source: str
    summary: str
    status: IncidentStatus
    created_at: str | None = None
    updated_at: str | None = None


class TimelineEvent(BaseModel):
    event: str
    actor: str
    detail: str
    created_at: str | None = None


class IncidentDetailResponse(BaseModel):
    incident: IncidentRecord
    plan: IncidentPlan | None
    timeline: list[TimelineEvent]


class IncidentListResponse(BaseModel):
    items: list[IncidentRecord]
    total: int


class MetricsSummaryResponse(BaseModel):
    total_incidents: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    approved_incidents: int
    mitigated_incidents: int


class IngestResponse(BaseModel):
    incident_id: str
    status: IncidentStatus


class PlanResponse(BaseModel):
    status: IncidentStatus
    plan: IncidentPlan


class ApprovalResponse(BaseModel):
    status: IncidentStatus
    approved_by: str


class ExecuteResponse(BaseModel):
    status: IncidentStatus
    summary: str

from __future__ import annotations

from app.models import IncidentRecord, IncidentPlan, PlanStep, Severity, StepType


def create_plan(record: IncidentRecord) -> IncidentPlan:
    runbook_id = f"rb-{record.service.lower().replace(' ', '-')}-001"

    base_steps = [
        PlanStep(
            id="s1",
            description="Fetch recent error rate, latency, saturation, and dependency health for the impacted service.",
            step_type=StepType.read_only,
        ),
        PlanStep(
            id="s2",
            description="Correlate latest deploys, config changes, and upstream incidents within the last 30 minutes.",
            step_type=StepType.read_only,
        ),
    ]

    if record.severity in {Severity.critical, Severity.high}:
        mitigation = PlanStep(
            id="s3",
            description="Prepare rollback or traffic-shift command and pause rollout until approved by incident commander.",
            step_type=StepType.write_action,
        )
        confidence = 0.87
        rationale = "High-severity signal with likely user impact; prioritize containment and reversible mitigation."
    else:
        mitigation = PlanStep(
            id="s3",
            description="Apply low-risk config mitigation in canary scope after approval.",
            step_type=StepType.write_action,
        )
        confidence = 0.78
        rationale = "Medium/low severity allows controlled mitigation after focused diagnostics."

    return IncidentPlan(
        incident_id=record.id,
        runbook_id=runbook_id,
        confidence=confidence,
        rationale=rationale,
        steps=base_steps + [mitigation],
    )

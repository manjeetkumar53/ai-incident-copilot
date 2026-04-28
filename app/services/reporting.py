from __future__ import annotations

from app.models import IncidentPlan, IncidentRecord, TimelineEvent


def build_audit_report(
    incident: IncidentRecord,
    plan: IncidentPlan | None,
    timeline: list[TimelineEvent],
) -> tuple[list[str], str]:
    controls = [
        "Plan generation required before approval",
        "Approval endpoint protected by incident role allowlist",
        "Execution endpoint protected by role and severity policy",
        "Every state transition recorded in the timeline",
    ]

    lines = [
        f"# Incident Audit Report: {incident.title}",
        "",
        f"- Incident ID: {incident.id}",
        f"- Service: {incident.service}",
        f"- Severity: {incident.severity.value}",
        f"- Source: {incident.source}",
        f"- Current status: {incident.status.value}",
        "",
        "## Plan",
    ]

    if plan is None:
        lines.append("- No plan generated")
    else:
        lines.extend(
            [
                f"- Runbook: {plan.runbook_id}",
                f"- Confidence: {plan.confidence:.2f}",
                f"- Rationale: {plan.rationale}",
                "",
                "## Planned Steps",
            ]
        )
        for step in plan.steps:
            lines.append(f"- {step.id}: [{step.step_type.value}] {step.description}")

    lines.extend(["", "## Controls"])
    for control in controls:
        lines.append(f"- {control}")

    lines.extend(["", "## Timeline"])
    for event in timeline:
        created_at = event.created_at or "n/a"
        lines.append(f"- {created_at}: {event.event} by {event.actor} - {event.detail}")

    return controls, "\n".join(lines)

from __future__ import annotations

from app.models import IncidentPlan, IncidentRecord, Severity


def check_execution_policy(incident: IncidentRecord, role: str, plan: IncidentPlan | None) -> tuple[bool, str]:
    if plan is None:
        return False, "Plan must exist before execution"

    # Critical incidents can only be executed by incident commander.
    if incident.severity == Severity.critical and role != "incident_commander":
        return False, "Critical incidents require incident_commander role for execution"

    # Guard against accidental execution when plan has no actionable write step.
    has_write_action = any(step.step_type == "write_action" for step in plan.steps)
    if not has_write_action:
        return False, "Plan has no write_action step to execute"

    return True, "allowed"

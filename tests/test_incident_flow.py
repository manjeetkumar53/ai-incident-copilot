from __future__ import annotations

from tests.conftest import client, reset_store


def test_happy_path_incident_flow() -> None:
    reset_store()

    ingest = client.post(
        "/v1/incidents/ingest",
        json={
            "title": "Checkout error spike",
            "service": "checkout-api",
            "severity": "critical",
            "source": "pagerduty",
            "summary": "5xx errors crossed SLO threshold",
        },
    )
    assert ingest.status_code == 201
    incident_id = ingest.json()["incident_id"]

    plan = client.post(f"/v1/incidents/{incident_id}/plan")
    assert plan.status_code == 200
    payload = plan.json()
    assert payload["status"] == "planned"
    assert payload["plan"]["steps"]
    assert payload["plan"]["runbook_id"].startswith("rb-")

    approve = client.post(
        f"/v1/incidents/{incident_id}/approve",
        json={"approved_by": "incident-commander", "comment": "Proceed with rollback"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    execute = client.post(
        f"/v1/incidents/{incident_id}/execute",
        json={"executed_by": "sre-oncall"},
    )
    assert execute.status_code == 200
    assert execute.json()["status"] == "mitigated"

    detail = client.get(f"/v1/incidents/{incident_id}")
    assert detail.status_code == 200
    timeline = detail.json()["timeline"]
    assert len(timeline) >= 4
    assert timeline[-1]["event"] == "incident.mitigated"


def test_execute_without_approval_fails() -> None:
    reset_store()

    ingest = client.post(
        "/v1/incidents/ingest",
        json={
            "title": "Latency increase",
            "service": "search-api",
            "severity": "high",
            "source": "webhook",
            "summary": "P95 latency doubled",
        },
    )
    incident_id = ingest.json()["incident_id"]

    client.post(f"/v1/incidents/{incident_id}/plan")

    execute = client.post(
        f"/v1/incidents/{incident_id}/execute",
        json={"executed_by": "sre-oncall"},
    )
    assert execute.status_code == 409
    assert "approved" in execute.json()["detail"]


def test_approve_without_plan_fails() -> None:
    reset_store()

    ingest = client.post(
        "/v1/incidents/ingest",
        json={
            "title": "Queue depth alert",
            "service": "worker-service",
            "severity": "medium",
            "source": "slack",
            "summary": "Backlog grew 4x",
        },
    )
    incident_id = ingest.json()["incident_id"]

    approve = client.post(
        f"/v1/incidents/{incident_id}/approve",
        json={"approved_by": "ic"},
    )
    assert approve.status_code == 409


def test_incident_not_found_returns_404() -> None:
    reset_store()

    plan = client.post("/v1/incidents/missing/plan")
    assert plan.status_code == 404

    detail = client.get("/v1/incidents/missing")
    assert detail.status_code == 404

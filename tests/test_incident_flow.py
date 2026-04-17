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
        headers={"X-Role": "incident_commander"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    execute = client.post(
        f"/v1/incidents/{incident_id}/execute",
        json={"executed_by": "incident-commander"},
        headers={"X-Role": "incident_commander"},
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
        headers={"X-Role": "sre_oncall"},
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
        headers={"X-Role": "incident_commander"},
    )
    assert approve.status_code == 409


def test_approve_with_forbidden_role_fails() -> None:
    reset_store()

    ingest = client.post(
        "/v1/incidents/ingest",
        json={
            "title": "Checkout DB pressure",
            "service": "checkout-db",
            "severity": "high",
            "source": "pagerduty",
            "summary": "CPU saturation reached 95%",
        },
    )
    incident_id = ingest.json()["incident_id"]
    client.post(f"/v1/incidents/{incident_id}/plan")

    approve = client.post(
        f"/v1/incidents/{incident_id}/approve",
        json={"approved_by": "developer"},
        headers={"X-Role": "developer"},
    )
    assert approve.status_code == 403


def test_critical_execute_by_sre_oncall_blocked_by_policy() -> None:
    reset_store()

    ingest = client.post(
        "/v1/incidents/ingest",
        json={
            "title": "Critical checkout outage",
            "service": "checkout-api",
            "severity": "critical",
            "source": "pagerduty",
            "summary": "Error rate 100% for checkout requests",
        },
    )
    incident_id = ingest.json()["incident_id"]
    client.post(f"/v1/incidents/{incident_id}/plan")
    client.post(
        f"/v1/incidents/{incident_id}/approve",
        json={"approved_by": "ic"},
        headers={"X-Role": "incident_commander"},
    )

    execute = client.post(
        f"/v1/incidents/{incident_id}/execute",
        json={"executed_by": "sre-oncall"},
        headers={"X-Role": "sre_oncall"},
    )
    assert execute.status_code == 403
    assert "Critical incidents require incident_commander" in execute.json()["detail"]


def test_integration_ingest_list_and_metrics() -> None:
    reset_store()

    ingest = client.post(
        "/v1/integrations/slack/ingest",
        json={
            "title": "Search latency warning",
            "service": "search-api",
            "severity": "medium",
            "summary": "P95 latency above threshold for 10 min",
            "external_id": "SLACK-123",
        },
    )
    assert ingest.status_code == 201
    incident_id = ingest.json()["incident_id"]

    listing = client.get("/v1/incidents?limit=10&offset=0")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 1
    assert any(item["id"] == incident_id for item in payload["items"])

    metrics = client.get("/v1/metrics/summary")
    assert metrics.status_code == 200
    mp = metrics.json()
    assert mp["total_incidents"] >= 1
    assert "by_status" in mp
    assert "by_severity" in mp


def test_incident_not_found_returns_404() -> None:
    reset_store()

    plan = client.post("/v1/incidents/missing/plan")
    assert plan.status_code == 404

    detail = client.get("/v1/incidents/missing")
    assert detail.status_code == 404

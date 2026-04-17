# AI Incident Copilot

AI Incident Copilot is an API-first incident response system that supports the full operational loop:

1. ingest alerts from external channels
2. generate mitigation plans
3. enforce human approval and role checks
4. execute approved actions under policy constraints
5. retain an auditable timeline and operational metrics

This repository is built as a production-oriented MVP with explicit safety controls and deterministic workflow behavior.

## Production-oriented capabilities

- Incident lifecycle state machine: `open -> planned -> approved -> executing -> mitigated`
- SQLite-backed persistence for incidents, plans, and timeline events
- Role-based access control on sensitive endpoints
- Execution policy checks for high-risk scenarios
- Integration ingest endpoint for PagerDuty/Slack/Webhook-style alerts
- Incident listing with filtering and pagination
- Metrics summary endpoint for operational reporting
- Typed request/response contracts via Pydantic models
- Automated tests for safety, policy, and workflow correctness

## Architecture

```text
External Alert Source (PagerDuty / Slack / Webhook)
                    |
                    v
      POST /v1/integrations/{source}/ingest
                    |
                    v
             Incident Store (SQLite)
                    |
                    +--> POST /v1/incidents/{id}/plan
                    |         |
                    |         v
                    |   Planner Service
                    |
                    +--> POST /v1/incidents/{id}/approve
                    |         |
                    |         v
                    |   RBAC (incident_commander, engineering_manager)
                    |
                    +--> POST /v1/incidents/{id}/execute
                              |
                              v
                     RBAC + Execution Policy
                    |
                    v
             Timeline + Metrics Summary
```

## Security and control model

### RBAC headers

Sensitive endpoints require `X-Role`:

- `POST /v1/incidents/{id}/approve`: `incident_commander` or `engineering_manager`
- `POST /v1/incidents/{id}/execute`: `incident_commander` or `sre_oncall`

If missing or invalid, API returns `403`.

### Execution policy

Additional policy checks run during execution:

- Critical incidents can only be executed by `incident_commander`
- Execution is blocked if no plan exists
- Execution is blocked if plan has no actionable `write_action` step

## Data model

### Incident

- `id`
- `title`
- `service`
- `severity`: `critical | high | medium | low`
- `source`: `pagerduty | slack | webhook`
- `summary`
- `status`
- `created_at`, `updated_at`

### Plan

- `incident_id`
- `runbook_id`
- `confidence`
- `rationale`
- `steps[]` with `read_only` / `write_action`

### Timeline event

- `event`
- `actor`
- `detail`
- `created_at`

## API reference

### Health

- `GET /health`

Returns:

```json
{"status": "ok"}
```

### Ingest incident (direct)

- `POST /v1/incidents/ingest`

Request:

```json
{
  "title": "Checkout error spike",
  "service": "checkout-api",
  "severity": "critical",
  "source": "pagerduty",
  "summary": "5xx errors crossed SLO threshold"
}
```

### Ingest incident (integration)

- `POST /v1/integrations/{source}/ingest`
- Supported `{source}`: `pagerduty`, `slack`, `webhook`

Request:

```json
{
  "title": "Search latency warning",
  "service": "search-api",
  "severity": "medium",
  "summary": "P95 latency above threshold for 10 minutes",
  "external_id": "ALERT-123"
}
```

### Generate plan

- `POST /v1/incidents/{incident_id}/plan`

### Approve plan (RBAC)

- `POST /v1/incidents/{incident_id}/approve`
- Required header: `X-Role: incident_commander` or `X-Role: engineering_manager`

### Execute plan (RBAC + policy)

- `POST /v1/incidents/{incident_id}/execute`
- Required header: `X-Role: incident_commander` or `X-Role: sre_oncall`

### Incident detail

- `GET /v1/incidents/{incident_id}`

### Incident list

- `GET /v1/incidents?status=<status>&severity=<severity>&limit=<n>&offset=<n>`

### Metrics summary

- `GET /v1/metrics/summary`

Response:

```json
{
  "total_incidents": 12,
  "by_status": {"open": 2, "approved": 4, "mitigated": 6},
  "by_severity": {"critical": 3, "high": 4, "medium": 3, "low": 2},
  "approved_incidents": 4,
  "mitigated_incidents": 6
}
```

## Local setup

```bash
cd /Users/manjeetkumar/Documents/ai-repos/ai-incident-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

## Quick operational flow (curl)

### 1) Ingest

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Checkout error spike",
    "service":"checkout-api",
    "severity":"critical",
    "source":"pagerduty",
    "summary":"5xx errors crossed SLO threshold"
  }'
```

### 2) Plan

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/plan
```

### 3) Approve (role required)

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/approve \
  -H "Content-Type: application/json" \
  -H "X-Role: incident_commander" \
  -d '{"approved_by":"incident-commander","comment":"Proceed with mitigation"}'
```

### 4) Execute (role + policy)

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/execute \
  -H "Content-Type: application/json" \
  -H "X-Role: incident_commander" \
  -d '{"executed_by":"incident-commander"}'
```

## Testing

Run all tests:

```bash
pytest -q
```

Current suite validates:

- health endpoint
- happy-path incident lifecycle
- execution blocked until approved
- approval blocked until plan exists
- forbidden role handling (`403`)
- critical execution policy enforcement
- integration ingest endpoint behavior
- incident list and metrics summary responses

Run only workflow tests:

```bash
pytest -q tests/test_incident_flow.py
## Repository structure

```text
ai-incident-copilot/
├── app/
│   ├── main.py
│   ├── models.py
│   └── services/
│       ├── authz.py
│       ├── planner.py
│       ├── policy.py
│       └── store.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_incident_flow.py
├── requirements.txt
└── README.md
```

## Next steps for enterprise hardening

- Replace header-based role checks with signed identity/JWT claims
- Migrate to Postgres + migration tooling (Alembic)
- Add async job worker for execution steps
- Add real integrations for PagerDuty/Slack APIs
- Add immutable audit log export and incident analytics dashboard

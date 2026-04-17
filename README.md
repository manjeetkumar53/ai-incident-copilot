# AI Incident Copilot

An API-first incident response assistant that proposes mitigation plans, enforces human approval before execution, and keeps a full incident timeline for auditability.

## Why this project

This project models a realistic SRE workflow for agentic systems:

- ingest incidents from alert channels
- generate actionable remediation plans
- require explicit approval before write actions
- execute only approved plans
- preserve an auditable incident timeline

## Core capabilities

- Human-in-the-loop approval gate before execution
- Structured incident lifecycle: `open -> planned -> approved -> executing -> mitigated`
- Rule-based planning with severity-aware steps
- Timeline events for incident traceability
- FastAPI API surface with typed request/response models
- Automated tests for happy path and safety constraints

## Architecture (Day 1)

```text
Alert Source (PagerDuty/Slack/Webhook)
                |
                v
      POST /v1/incidents/ingest
                |
                v
         Incident Store (in-memory)
                |
                +--> POST /v1/incidents/{id}/plan
                |         |
                |         v
                |     Planner Service
                |
                +--> POST /v1/incidents/{id}/approve
                |         |
                |         v
                |   Approval Timeline Event
                |
                +--> POST /v1/incidents/{id}/execute
                          |
                          v
                    Mitigation Status
```

## Quick start

```bash
cd /Users/manjeetkumar/Documents/ai-repos/ai-incident-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger docs: http://127.0.0.1:8000/docs

## API endpoints

- `GET /health`
- `POST /v1/incidents/ingest`
- `POST /v1/incidents/{incident_id}/plan`
- `POST /v1/incidents/{incident_id}/approve`
- `POST /v1/incidents/{incident_id}/execute`
- `GET /v1/incidents/{incident_id}`

## Example flow

### 1) Ingest incident

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

### 2) Generate plan

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/plan
```

### 3) Approve plan

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by":"incident-commander","comment":"Proceed with rollback"}'
```

### 4) Execute approved plan

```bash
curl -s -X POST http://127.0.0.1:8000/v1/incidents/<INCIDENT_ID>/execute \
  -H "Content-Type: application/json" \
  -d '{"executed_by":"sre-oncall"}'
```

## How to test

Run full suite:

```bash
pytest -q
```

Current tests cover:

- health endpoint
- complete incident lifecycle (ingest -> plan -> approve -> execute)
- blocked execution without approval
- blocked approval without plan
- 404 behavior for unknown incident IDs

Run specific test file:

```bash
pytest -q tests/test_incident_flow.py
```

## Next milestones

- Add RBAC roles (IC, approver, executor)
- Persist incidents and timeline in Postgres
- Async execution worker queue
- Slack/PagerDuty adapters
- Policy engine for action allowlists
- Ops dashboard with MTTR metrics

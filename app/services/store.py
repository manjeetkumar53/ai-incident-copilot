from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from app.models import IncidentPlan, IncidentRecord, TimelineEvent


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    service TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    incident_id TEXT PRIMARY KEY,
                    runbook_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    rationale TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES incidents(id)
                )
                """
            )

    def add_incident(self, record: IncidentRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO incidents (id, title, service, severity, source, summary, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.title,
                    record.service,
                    record.severity.value,
                    record.source,
                    record.summary,
                    record.status.value,
                ),
            )

    def add_plan(self, incident_id: str, plan: IncidentPlan) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO plans (incident_id, runbook_id, confidence, rationale, steps_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    plan.runbook_id,
                    plan.confidence,
                    plan.rationale,
                    json.dumps([s.model_dump(mode="json") for s in plan.steps]),
                ),
            )

    def add_timeline_event(self, incident_id: str, event: TimelineEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO timeline_events (incident_id, event, actor, detail)
                VALUES (?, ?, ?, ?)
                """,
                (incident_id, event.event, event.actor, event.detail),
            )

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, service, severity, source, summary, status
                FROM incidents WHERE id = ?
                """,
                (incident_id,),
            ).fetchone()
        if row is None:
            return None
        return IncidentRecord(
            id=row[0],
            title=row[1],
            service=row[2],
            severity=row[3],
            source=row[4],
            summary=row[5],
            status=row[6],
        )

    def update_incident_status(self, incident_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE incidents SET status = ? WHERE id = ?", (status, incident_id))

    def get_plan(self, incident_id: str) -> IncidentPlan | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT incident_id, runbook_id, confidence, rationale, steps_json
                FROM plans WHERE incident_id = ?
                """,
                (incident_id,),
            ).fetchone()
        if row is None:
            return None
        steps = json.loads(row[4])
        return IncidentPlan(
            incident_id=row[0],
            runbook_id=row[1],
            confidence=row[2],
            rationale=row[3],
            steps=steps,
        )

    def get_timeline(self, incident_id: str) -> list[TimelineEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event, actor, detail
                FROM timeline_events
                WHERE incident_id = ?
                ORDER BY id ASC
                """,
                (incident_id,),
            ).fetchall()
        return [TimelineEvent(event=r[0], actor=r[1], detail=r[2]) for r in rows]

    def clear_all(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM timeline_events")
            conn.execute("DELETE FROM plans")
            conn.execute("DELETE FROM incidents")


store = SQLiteStore(Path(os.getenv("INCIDENT_DB", "incident_copilot.db")))

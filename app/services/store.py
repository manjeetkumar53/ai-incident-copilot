from __future__ import annotations

from dataclasses import dataclass, field

from app.models import IncidentPlan, IncidentRecord, TimelineEvent


@dataclass
class InMemoryStore:
    incidents: dict[str, IncidentRecord] = field(default_factory=dict)
    plans: dict[str, IncidentPlan] = field(default_factory=dict)
    timeline: dict[str, list[TimelineEvent]] = field(default_factory=dict)

    def add_incident(self, record: IncidentRecord) -> None:
        self.incidents[record.id] = record
        self.timeline.setdefault(record.id, [])

    def add_plan(self, incident_id: str, plan: IncidentPlan) -> None:
        self.plans[incident_id] = plan

    def add_timeline_event(self, incident_id: str, event: TimelineEvent) -> None:
        self.timeline.setdefault(incident_id, []).append(event)


store = InMemoryStore()

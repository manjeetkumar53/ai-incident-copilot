from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.services.store import store


client = TestClient(app)


def reset_store() -> None:
    store.incidents.clear()
    store.plans.clear()
    store.timeline.clear()

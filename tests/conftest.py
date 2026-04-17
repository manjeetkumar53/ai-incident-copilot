from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["INCIDENT_DB"] = _tmp.name

from app.main import app
from app.services.store import store


client = TestClient(app)


def reset_store() -> None:
    store.clear_all()

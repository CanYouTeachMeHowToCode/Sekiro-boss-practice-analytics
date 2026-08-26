import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import attempt_service, boss_service

ORIGINAL_DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy(ORIGINAL_DATA_DIR / "bosses.json", data_dir / "bosses.json")
    (data_dir / "attempts.json").write_text("[]", encoding="utf-8")

    monkeypatch.setattr(boss_service, "DATA_DIR", data_dir)
    monkeypatch.setattr(attempt_service, "DATA_DIR", data_dir)

    return TestClient(app)

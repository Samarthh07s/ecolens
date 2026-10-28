"""Every test gets its own empty SQLite file, so tests never touch ecolens.db."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    import config
    import database
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(config, "HTTP_BACKOFF_SECONDS", 0)
    database.init_db()
    yield path

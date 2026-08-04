from __future__ import annotations

from app.core.bootstrap import initialize_database


def test_initialize_database_handles_missing_db_gracefully():
    result = initialize_database()
    assert result["status"] in {"initialized", "skipped"}

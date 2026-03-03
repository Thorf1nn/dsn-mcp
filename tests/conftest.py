from __future__ import annotations

from pathlib import Path

import pytest

from dsn_mcp.store import DSNDataStore


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def store(data_dir: Path) -> DSNDataStore:
    s = DSNDataStore()
    s.load_all_versions(data_dir)
    return s

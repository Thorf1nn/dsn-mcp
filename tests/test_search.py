from __future__ import annotations

from dsn_mcp.search import search_enumerations, search_rubriques
from dsn_mcp.store import DSNDataStore


def test_search_by_code(store: DSNDataStore) -> None:
    ct = store.versions[store.default_version]
    results = search_rubriques(ct, "S21.G00.40.001")
    assert len(results) >= 1
    assert results[0][1].code == "S21.G00.40.001"
    assert results[0][2] == 100  # exact match score


def test_search_by_keyword(store: DSNDataStore) -> None:
    ct = store.versions[store.default_version]
    results = search_rubriques(ct, "contrat")
    assert len(results) > 0


def test_search_empty_query(store: DSNDataStore) -> None:
    ct = store.versions[store.default_version]
    results = search_rubriques(ct, "")
    assert results == []


def test_search_enumerations(store: DSNDataStore) -> None:
    ct = store.versions[store.default_version]
    results = search_enumerations(ct, "maladie")
    assert len(results) > 0


def test_search_limit(store: DSNDataStore) -> None:
    ct = store.versions[store.default_version]
    results = search_rubriques(ct, "date", limit=3)
    assert len(results) <= 3

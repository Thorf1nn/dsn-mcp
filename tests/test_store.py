from __future__ import annotations

import pytest

from dsn_mcp.store import DSNDataStore


def test_load_versions(store: DSNDataStore) -> None:
    versions = store.list_versions()
    assert len(versions) >= 1
    assert store.default_version in versions


def test_list_blocs(store: DSNDataStore) -> None:
    blocs = store.list_blocs()
    assert len(blocs) > 0
    codes = [b.code for b in blocs]
    assert "S21.G00.40" in codes


def test_get_bloc(store: DSNDataStore) -> None:
    bloc = store.get_bloc("S21.G00.40")
    assert bloc is not None
    assert bloc.code == "S21.G00.40"
    assert len(bloc.rubriques) > 50  # Contrat a 75+ rubriques


def test_get_bloc_not_found(store: DSNDataStore) -> None:
    bloc = store.get_bloc("S99.G99.99")
    assert bloc is None


def test_get_rubrique(store: DSNDataStore) -> None:
    bloc, rub = store.get_rubrique("S21.G00.40.001")
    assert rub is not None
    assert bloc is not None
    assert rub.code == "S21.G00.40.001"
    assert bloc.code == "S21.G00.40"


def test_get_rubrique_not_found(store: DSNDataStore) -> None:
    bloc, rub = store.get_rubrique("S99.G99.99.999")
    assert bloc is None
    assert rub is None


def test_get_controls(store: DSNDataStore) -> None:
    controls = store.get_controls("S21.G00.40")
    assert len(controls["cch"]) > 0


def test_get_controls_filter(store: DSNDataStore) -> None:
    controls = store.get_controls("S21.G00.40", control_type="cch")
    assert len(controls["cch"]) > 0
    assert len(controls["sig"]) == 0
    assert len(controls["csl"]) == 0


def test_resolve_version_error(store: DSNDataStore) -> None:
    with pytest.raises(ValueError, match="non chargée"):
        store._resolve_version("9999")

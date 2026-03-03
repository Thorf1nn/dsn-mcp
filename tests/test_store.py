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


def test_bloc_names_clean(store: DSNDataStore) -> None:
    """Vérifie que les noms de blocs sont propres (pas de bruit du PDF)."""
    bloc = store.get_bloc("S21.G00.40")
    assert bloc is not None
    assert bloc.name == "Contrat (contrat de travail, convention, mandat)"

    bloc_ind = store.get_bloc("S21.G00.30")
    assert bloc_ind is not None
    assert bloc_ind.name == "Individu"


def test_rubrique_enumerations(store: DSNDataStore) -> None:
    """Vérifie que S21.G00.40.007 (Nature du contrat) a ses énumérations."""
    _, rub = store.get_rubrique("S21.G00.40.007")
    assert rub is not None
    assert rub.enumeration is not None
    assert len(rub.enumeration) >= 20  # 26 valeurs attendues
    codes = [e.code for e in rub.enumeration]
    assert "01" in codes  # CDI
    assert "02" in codes  # CDD


def test_rubrique_data_quality(store: DSNDataStore) -> None:
    """Vérifie la qualité des données d'une rubrique."""
    _, rub = store.get_rubrique("S21.G00.40.001")
    assert rub is not None
    assert rub.label == "Date de début du contrat"
    assert rub.technical_name == "Contrat.DateDebut"
    assert rub.data_type == "D"
    assert rub.description is not None
    assert len(rub.description) > 50

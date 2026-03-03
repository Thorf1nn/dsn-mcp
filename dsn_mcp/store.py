from __future__ import annotations

import json
import logging
from pathlib import Path

from dsn_mcp.models import (
    Bloc,
    CahierTechnique,
    Combinaison,
    CombinaisonsTable,
    Nomenclatures,
    NomenclatureTable,
    Rubrique,
    UsageEntry,
    UsageTable,
    VersionMetadata,
)

logger = logging.getLogger(__name__)


class DSNDataStore:
    """Charge et requête les données du Cahier Technique DSN pré-parsées en JSON."""

    def __init__(self) -> None:
        self.versions: dict[str, CahierTechnique] = {}
        self.usages: dict[str, UsageTable] = {}
        self.nomenclatures: dict[str, Nomenclatures] = {}
        self.combinaisons: dict[str, CombinaisonsTable] = {}
        self.metadata: dict[str, VersionMetadata] = {}
        self.default_version: str = ""

    def load_all_versions(self, data_dir: Path, default_version: str | None = None) -> None:
        """Découvre et charge toutes les versions disponibles dans data_dir."""
        if not data_dir.exists():
            logger.warning("Data directory %s does not exist", data_dir)
            return

        for version_dir in sorted(data_dir.iterdir()):
            if version_dir.is_dir() and (version_dir / "ct.json").exists():
                version = version_dir.name
                self.load_version(version, version_dir)

        if default_version and default_version in self.versions:
            self.default_version = default_version
        elif self.versions:
            self.default_version = sorted(self.versions.keys())[-1]

        logger.info(
            "Loaded %d version(s): %s (default: %s)",
            len(self.versions),
            list(self.versions.keys()),
            self.default_version,
        )

    def load_version(self, version: str, data_dir: Path) -> None:
        """Charge une version du CT depuis les fichiers JSON pré-parsés."""
        ct_path = data_dir / "ct.json"
        if ct_path.exists():
            with open(ct_path, encoding="utf-8") as f:
                self.versions[version] = CahierTechnique.model_validate(json.load(f))
            logger.info("Loaded CT %s: %d blocs", version, len(self.versions[version].blocs))

        usages_path = data_dir / "usages.json"
        if usages_path.exists():
            with open(usages_path, encoding="utf-8") as f:
                self.usages[version] = UsageTable.model_validate(json.load(f))

        nomenclatures_path = data_dir / "nomenclatures.json"
        if nomenclatures_path.exists():
            with open(nomenclatures_path, encoding="utf-8") as f:
                self.nomenclatures[version] = Nomenclatures.model_validate(json.load(f))

        combinaisons_path = data_dir / "combinaisons.json"
        if combinaisons_path.exists():
            with open(combinaisons_path, encoding="utf-8") as f:
                self.combinaisons[version] = CombinaisonsTable.model_validate(json.load(f))

        metadata_path = data_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, encoding="utf-8") as f:
                self.metadata[version] = VersionMetadata.model_validate(json.load(f))

    def _resolve_version(self, version: str | None) -> str:
        """Résout la version à utiliser (paramètre ou défaut)."""
        v = version or self.default_version
        if v not in self.versions:
            raise ValueError(f"Version '{v}' non chargée. Versions disponibles : {list(self.versions.keys())}")
        return v

    def list_versions(self) -> list[str]:
        return sorted(self.versions.keys())

    def get_bloc(self, bloc_code: str, version: str | None = None) -> Bloc | None:
        v = self._resolve_version(version)
        return self.versions[v].blocs.get(bloc_code)

    def list_blocs(self, version: str | None = None) -> list[Bloc]:
        v = self._resolve_version(version)
        return sorted(self.versions[v].blocs.values(), key=lambda b: b.code)

    def get_rubrique(self, rubrique_code: str, version: str | None = None) -> tuple[Bloc | None, Rubrique | None]:
        """Retourne le bloc parent et la rubrique, ou (None, None) si non trouvé."""
        v = self._resolve_version(version)
        # Le code bloc = les 3 premières parties du code rubrique
        parts = rubrique_code.rsplit(".", 1)
        if len(parts) == 2:
            bloc_code = parts[0]
            bloc = self.versions[v].blocs.get(bloc_code)
            if bloc:
                rub = bloc.rubriques.get(rubrique_code)
                if rub:
                    return bloc, rub
        # Recherche exhaustive si le code n'a pas le format attendu
        for bloc in self.versions[v].blocs.values():
            if rubrique_code in bloc.rubriques:
                return bloc, bloc.rubriques[rubrique_code]
        return None, None

    def get_usage(self, rubrique_code: str, version: str | None = None) -> UsageEntry | None:
        v = self._resolve_version(version)
        if v not in self.usages:
            return None
        return self.usages[v].usages.get(rubrique_code)

    def get_controls(
        self, code: str, control_type: str | None = None, version: str | None = None
    ) -> dict[str, list]:
        """Retourne les contrôles pour une rubrique ou un bloc entier."""
        v = self._resolve_version(version)
        result: dict[str, list] = {"cch": [], "sig": [], "csl": []}

        rubriques: list[Rubrique] = []
        bloc = self.versions[v].blocs.get(code)
        if bloc:
            rubriques = list(bloc.rubriques.values())
        else:
            _, rub = self.get_rubrique(code, v)
            if rub:
                rubriques = [rub]

        for rub in rubriques:
            if not control_type or control_type.lower() == "cch":
                result["cch"].extend(rub.cch_controls)
            if not control_type or control_type.lower() == "sig":
                result["sig"].extend(rub.sig_controls)
            if not control_type or control_type.lower() == "csl":
                result["csl"].extend(rub.csl_controls)

        return result

    def get_combinaisons(self, bloc_code: str, version: str | None = None) -> list[Combinaison]:
        v = self._resolve_version(version)
        if v not in self.combinaisons:
            return []
        return [c for c in self.combinaisons[v].rules if c.bloc == bloc_code]

    def get_nomenclature(self, table_name: str, version: str | None = None) -> NomenclatureTable | None:
        v = self._resolve_version(version)
        if v not in self.nomenclatures:
            return None
        return self.nomenclatures[v].tables.get(table_name)

    def list_nomenclatures(self, version: str | None = None) -> list[str]:
        v = self._resolve_version(version)
        if v not in self.nomenclatures:
            return []
        return sorted(self.nomenclatures[v].tables.keys())

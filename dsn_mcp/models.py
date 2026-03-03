from __future__ import annotations

from pydantic import BaseModel


class CslControl(BaseModel):
    """Contrôle de format (CSL) - vérifie le pattern d'une rubrique."""

    id: str
    pattern: str
    description: str = ""


class CchControl(BaseModel):
    """Contrôle de cohérence bloquant (CCH) - vérifie les règles inter-rubriques."""

    id: str
    rule_text: str
    severity: str = "blocking"
    references: list[str] = []


class SigControl(BaseModel):
    """Signal non-bloquant (SIG) - avertissement de consigne."""

    id: str
    rule_text: str
    severity: str = "warning"


class EnumValue(BaseModel):
    """Valeur d'une énumération (ex: '01 - CDI de droit privé')."""

    code: str
    label: str


class Rubrique(BaseModel):
    """Une rubrique DSN (champ) au sein d'un bloc."""

    code: str  # ex: "S21.G00.40.007"
    label: str  # ex: "Nature du contrat"
    technical_name: str | None = None  # ex: "Contrat.Nature"
    description: str | None = None
    data_type: str = "X"  # X=alphanumérique, N=numérique, D=date
    length_min: int = 0
    length_max: int = 0
    format_regex: str | None = None
    csl_controls: list[CslControl] = []
    cch_controls: list[CchControl] = []
    sig_controls: list[SigControl] = []
    enumeration: list[EnumValue] | None = None
    category: str | None = None


class Bloc(BaseModel):
    """Un bloc DSN regroupant des rubriques (ex: S21.G00.40 = Contrat)."""

    code: str  # ex: "S21.G00.40"
    name: str  # ex: "Contrat"
    description: str | None = None
    parent_bloc: str | None = None
    rubriques: dict[str, Rubrique] = {}


class CahierTechnique(BaseModel):
    """Représentation complète d'une version du Cahier Technique DSN."""

    version: str  # ex: "CT2026.1.2"
    extraction_date: str = ""
    source_hash: str = ""
    blocs: dict[str, Bloc] = {}


class UsageEntry(BaseModel):
    """Statut d'usage d'une rubrique par modèle de déclaration."""

    model_01: str | None = None  # DSN mensuelle
    model_04: str | None = None  # Signalement arrêt de travail
    model_05: str | None = None  # Signalement reprise
    model_07: str | None = None  # Signalement fin de contrat (FCTU)
    model_08: str | None = None  # DSN d'amorçage
    model_09: str | None = None  # DSN de substitution


DECLARATION_MODELS = {
    "01": "DSN mensuelle",
    "04": "Signalement arrêt de travail",
    "05": "Signalement reprise suite à arrêt de travail",
    "07": "Signalement fin de contrat de travail unique (FCTU)",
    "08": "DSN d'amorçage",
    "09": "DSN de substitution",
}


class UsageTable(BaseModel):
    """Table des usages : matrice rubrique × modèle de déclaration."""

    version: str
    usages: dict[str, UsageEntry] = {}


class Combinaison(BaseModel):
    """Règle de combinaison valide de codes pour un bloc."""

    bloc: str
    description: str = ""
    fields: list[str] = []
    valid_combinations: list[dict[str, str]] = []


class CombinaisonsTable(BaseModel):
    """Ensemble des règles de combinaison pour une version CT."""

    version: str
    rules: list[Combinaison] = []


class NomenclatureTable(BaseModel):
    """Table de nomenclature externe (IDCC, NAF, etc.)."""

    name: str
    description: str = ""
    values: list[EnumValue] = []


class Nomenclatures(BaseModel):
    """Ensemble des tables de nomenclature pour une version CT."""

    version: str
    tables: dict[str, NomenclatureTable] = {}


class VersionMetadata(BaseModel):
    """Métadonnées d'une version extraite du CT."""

    ct_version: str
    norm_year: int
    publication_date: str = ""
    extraction_date: str = ""
    stats: dict[str, int] = {}

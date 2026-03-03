"""Extraction des données du Cahier Technique DSN depuis le PDF.

Parse le PDF pour extraire :
- Les blocs (S21.G00.XX) avec leurs descriptions
- Les rubriques (S21.G00.XX.YYY) avec libellés, types, formats, énumérations
- Les contrôles CCH (bloquants), SIG (signalements), CSL (format)

Usage :
    python -m scripts.extract_pdf <chemin_pdf> <dossier_sortie>
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

# === Patterns regex ===

# En-tête de bloc : "S21.G00.40" seul ou suivi d'un nom
BLOC_HEADER_RE = re.compile(
    r"^(S\d{2}\.G\d{2}\.\d{2})\s*$"
)

# Ligne de rubrique : "Code label S21.G00.40.007" ou "label S21.G00.40.007"
RUBRIQUE_LINE_RE = re.compile(
    r"(S\d{2}\.G\d{2}\.\d{2}\.\d{3})"
)

# Nom technique : "Contrat.Nature" (PascalCase.PascalCase)
TECHNICAL_NAME_RE = re.compile(
    r"^([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]*)*\.[A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]*)*)$"
)

# Contrôle CCH : "CCH-11 :" ou "CCH-S21... :"
CCH_RE = re.compile(r"(CCH-\d+)\s*:\s*(.*)")

# Contrôle SIG
SIG_RE = re.compile(r"(SIG-\d+)\s*:\s*(.*)")

# Contrôle CSL
CSL_RE = re.compile(r"CSL\s*\d*\s*:\s*(.*)")

# Valeur d'énumération : "01 - CDI de droit privé"
ENUM_RE = re.compile(r"^(\d{2,3})\s*-\s*(.+)$")

# Type de données + longueur : "X [2,2]" ou "N [4,18]" ou "D [8,8]"
TYPE_LENGTH_RE = re.compile(r"\b([XND])\b.*?\[(\d+),(\d+)\]")

# Format CSL dans le texte : "CSL 00 : pattern"
CSL_INLINE_RE = re.compile(r"CSL\s+(\d+)\s*:\s*(.+?)(?:\n|$)")

# Bloc avec nom sur la même ligne : "S21.G00.40\nContrat (contrat de travail, ...)"
BLOC_WITH_NAME_RE = re.compile(
    r"(S\d{2}\.G\d{2}\.\d{2})\s*\n\s*(.+?)(?:\s+S\d{2}\.G\d{2}\.\d{2}\s*$|\n)",
    re.MULTILINE,
)


@dataclass
class ExtractedRubrique:
    code: str
    label: str
    technical_name: str | None = None
    description: str | None = None
    data_type: str = "X"
    length_min: int = 0
    length_max: int = 0
    format_regex: str | None = None
    csl_controls: list[dict] = field(default_factory=list)
    cch_controls: list[dict] = field(default_factory=list)
    sig_controls: list[dict] = field(default_factory=list)
    enumeration: list[dict] | None = None

    def to_dict(self) -> dict:
        d = {
            "code": self.code,
            "label": self.label,
            "technical_name": self.technical_name,
            "description": self.description,
            "data_type": self.data_type,
            "length_min": self.length_min,
            "length_max": self.length_max,
            "format_regex": self.format_regex,
            "csl_controls": self.csl_controls,
            "cch_controls": self.cch_controls,
            "sig_controls": self.sig_controls,
            "enumeration": self.enumeration,
        }
        return d


@dataclass
class ExtractedBloc:
    code: str
    name: str
    description: str | None = None
    parent_bloc: str | None = None
    rubriques: dict[str, ExtractedRubrique] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "parent_bloc": self.parent_bloc,
            "rubriques": {k: v.to_dict() for k, v in sorted(self.rubriques.items())},
        }


def extract_from_pdf(pdf_path: str | Path) -> dict[str, ExtractedBloc]:
    """Extrait tous les blocs et rubriques du cahier technique PDF."""
    pdf_path = Path(pdf_path)
    logger.info("Ouverture du PDF : %s", pdf_path)

    pdf = pdfplumber.open(pdf_path)
    total_pages = len(pdf.pages)
    logger.info("Total pages : %d", total_pages)

    # Phase 1 : Extraire le texte page par page
    pages_text: list[str] = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        pages_text.append(text)

    # Phase 2 : Identifier les sections de blocs
    # Les blocs commencent aux pages dont l'en-tête contient "S21.G00.XX date"
    blocs: dict[str, ExtractedBloc] = {}
    current_bloc_code: str | None = None
    current_bloc_pages: list[int] = []

    # Trouver les pages de début de chaque bloc
    bloc_starts: list[tuple[int, str]] = []
    header_re = re.compile(r"^(S\d{2}\.G\d{2}\.\d{2})\s+\d{4}-\d{2}-\d{2}")

    for i, text in enumerate(pages_text):
        lines = text.strip().split("\n")
        if lines:
            m = header_re.match(lines[0].strip())
            if m:
                bloc_code = m.group(1)
                if not bloc_starts or bloc_starts[-1][1] != bloc_code:
                    bloc_starts.append((i, bloc_code))

    logger.info("Blocs détectés : %d", len(bloc_starts))
    for page_num, code in bloc_starts:
        logger.debug("  Page %d : %s", page_num + 1, code)

    # Phase 3 : Parser chaque section de bloc
    for idx, (start_page, bloc_code) in enumerate(bloc_starts):
        # Déterminer la fin de la section
        if idx + 1 < len(bloc_starts):
            end_page = bloc_starts[idx + 1][0]
        else:
            end_page = total_pages

        # Concaténer le texte de toutes les pages de ce bloc
        bloc_text = "\n".join(pages_text[start_page:end_page])

        # Parser le bloc
        bloc = _parse_bloc(bloc_code, bloc_text)
        if bloc_code not in blocs:
            blocs[bloc_code] = bloc
        else:
            # Fusionner les rubriques si le bloc apparaît sur plusieurs sections
            blocs[bloc_code].rubriques.update(bloc.rubriques)

    logger.info(
        "Extraction terminée : %d blocs, %d rubriques",
        len(blocs),
        sum(len(b.rubriques) for b in blocs.values()),
    )

    pdf.close()
    return blocs


def _parse_bloc(bloc_code: str, text: str) -> ExtractedBloc:
    """Parse le texte d'un bloc pour extraire nom, description et rubriques."""
    lines = text.split("\n")

    # Trouver le nom du bloc
    # Pattern : le nom apparaît juste après la première occurrence du code bloc
    # suivi d'un label, ex: "Contrat (contrat de travail, convention, mandat)"
    bloc_name = ""
    bloc_description = ""

    # Chercher le nom dans les premières lignes
    name_found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Chercher la ligne qui a le code bloc suivi du nom
        # Ex: "S21.G00.40\nContrat (contrat de travail..."
        # Ou: "Contrat (contrat de travail, convention, mandat) S21.G00.40"
        if bloc_code in stripped and not name_found:
            # Le nom pourrait être sur la même ligne après le code
            after_code = stripped.replace(bloc_code, "").strip()
            # Ou la ligne contient "NomBloc S21.G00.XX"
            parts = stripped.split(bloc_code)
            for p in parts:
                p = p.strip().rstrip("-").strip()
                if p and len(p) > 2 and not p.startswith("20") and not re.match(r"\d{4}-\d{2}", p):
                    bloc_name = p
                    name_found = True
                    break
            if not name_found and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Vérifier si la ligne suivante est le nom (pas une date, pas un code)
                if (
                    next_line
                    and not re.match(r"\d{4}-\d{2}", next_line)
                    and not re.match(r"S\d{2}\.", next_line)
                    and len(next_line) > 2
                ):
                    bloc_name = next_line
                    name_found = True

    # Nettoyage du nom
    bloc_name = re.sub(r"\s+S\d{2}\.G\d{2}\.\d{2}$", "", bloc_name).strip()
    if not bloc_name:
        bloc_name = bloc_code

    # Extraire les rubriques
    rubriques = _extract_rubriques(bloc_code, text)

    return ExtractedBloc(
        code=bloc_code,
        name=bloc_name,
        description=bloc_description or None,
        rubriques=rubriques,
    )


def _extract_rubriques(bloc_code: str, text: str) -> dict[str, ExtractedRubrique]:
    """Extrait toutes les rubriques d'un bloc à partir du texte."""
    rubriques: dict[str, ExtractedRubrique] = {}

    # Trouver toutes les positions de codes rubrique dans le texte
    rub_pattern = re.compile(rf"({re.escape(bloc_code)}\.\d{{3}})")
    all_positions: list[tuple[int, str]] = []

    for m in rub_pattern.finditer(text):
        code = m.group(1)
        pos = m.start()
        all_positions.append((pos, code))

    if not all_positions:
        return rubriques

    # Regrouper les occurrences par code de rubrique
    # La première occurrence d'un code est généralement la liste en haut du bloc
    # La deuxième occurrence est la définition détaillée
    code_occurrences: dict[str, list[int]] = {}
    for pos, code in all_positions:
        if code not in code_occurrences:
            code_occurrences[code] = []
        code_occurrences[code].append(pos)

    # Pour chaque rubrique avec au moins 2 occurrences, la 2ème est la définition
    # Pour celles avec 1 seule occurrence, c'est soit la liste soit une référence
    rubrique_defs: list[tuple[int, str]] = []
    for code, positions in code_occurrences.items():
        if len(positions) >= 2:
            # La 2ème occurrence est la définition détaillée
            rubrique_defs.append((positions[1], code))
        elif len(positions) == 1:
            # Vérifier si c'est une définition (suivie d'un nom technique)
            pos = positions[0]
            after = text[pos : pos + 200]
            if TECHNICAL_NAME_RE.search(after.replace("\n", " ")):
                rubrique_defs.append((pos, code))

    rubrique_defs.sort(key=lambda x: x[0])

    # Extraire le texte de chaque rubrique
    for idx, (pos, code) in enumerate(rubrique_defs):
        # Texte jusqu'à la prochaine rubrique
        if idx + 1 < len(rubrique_defs):
            end_pos = rubrique_defs[idx + 1][0]
        else:
            end_pos = len(text)

        rub_text = text[pos:end_pos]
        rub = _parse_rubrique(code, rub_text)
        if rub and rub.label:
            rubriques[code] = rub

    return rubriques


def _parse_rubrique(code: str, text: str) -> ExtractedRubrique | None:
    """Parse le texte d'une rubrique pour extraire ses attributs."""
    lines = text.split("\n")
    if not lines:
        return None

    rub = ExtractedRubrique(code=code, label="")

    # Extraire le libellé : c'est le texte avant le code sur la même ligne
    # ou la ligne précédant le code
    first_line = lines[0].strip()
    label_match = re.match(rf"(.+?)\s+{re.escape(code)}", first_line)
    if label_match:
        rub.label = label_match.group(1).strip()
    else:
        # Le label pourrait être sur la ligne avec le code
        rub.label = first_line.replace(code, "").strip()

    # Nettoyer le label
    rub.label = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", rub.label)
    rub.label = re.sub(r"\s+$", "", rub.label)
    if not rub.label or rub.label == code:
        # Chercher dans les lignes suivantes
        for line in lines[1:5]:
            stripped = line.strip()
            if stripped and not re.match(r"S\d{2}\.", stripped) and len(stripped) > 3:
                rub.label = stripped
                break

    # Chercher le nom technique
    for line in lines[:10]:
        m = TECHNICAL_NAME_RE.match(line.strip())
        if m:
            rub.technical_name = m.group(1)
            break

    # Chercher la description (texte prose après le nom technique)
    desc_lines = []
    in_desc = False
    for line in lines[1:]:
        stripped = line.strip()
        if rub.technical_name and stripped == rub.technical_name:
            in_desc = True
            continue
        if in_desc:
            if CCH_RE.match(stripped) or SIG_RE.match(stripped) or CSL_RE.match(stripped):
                break
            if ENUM_RE.match(stripped):
                break
            if TYPE_LENGTH_RE.search(stripped):
                break
            if re.match(r"^(S\d{2}\.G\d{2}\.\d{2}\.\d{3})$", stripped):
                break
            if stripped:
                desc_lines.append(stripped)
            if len(desc_lines) > 5:
                break

    if desc_lines:
        rub.description = " ".join(desc_lines)

    # Chercher type et longueur
    for line in lines:
        m = TYPE_LENGTH_RE.search(line)
        if m:
            rub.data_type = m.group(1)
            rub.length_min = int(m.group(2))
            rub.length_max = int(m.group(3))
            break

    # Pour les dates, déduire le type
    if "date" in rub.label.lower() or (rub.technical_name and "Date" in rub.technical_name):
        if rub.data_type == "X" and rub.length_min == 0:
            rub.data_type = "D"
            rub.length_min = 8
            rub.length_max = 8

    # Extraire les contrôles CSL (format regex)
    for m in CSL_INLINE_RE.finditer(text):
        pattern = m.group(2).strip()
        rub.format_regex = pattern
        rub.csl_controls.append({
            "id": f"CSL-{m.group(1)}",
            "pattern": pattern,
            "description": f"Format de {rub.label}",
        })

    # Extraire les contrôles CCH
    for m in CCH_RE.finditer(text):
        cch_id = m.group(1)
        rule_text = m.group(2).strip()
        # Capturer la suite du texte jusqu'au prochain CCH/SIG ou ligne vide
        start = m.end()
        remaining = text[start:]
        continuation_lines = []
        for rline in remaining.split("\n"):
            rstripped = rline.strip()
            if not rstripped:
                break
            if CCH_RE.match(rstripped) or SIG_RE.match(rstripped):
                break
            if re.match(r"^(S\d{2}\.G\d{2}\.\d{2}\.\d{3})$", rstripped):
                break
            continuation_lines.append(rstripped)

        full_rule = rule_text + " " + " ".join(continuation_lines) if continuation_lines else rule_text
        full_rule = full_rule.strip()

        # Extraire les références (codes rubrique mentionnés)
        refs = re.findall(r"S\d{2}\.G\d{2}\.\d{2}\.\d{3}", full_rule)
        # Enlever le code de la rubrique courante des refs
        refs = [r for r in refs if r != code]

        rub.cch_controls.append({
            "id": cch_id,
            "rule_text": full_rule[:500],
            "severity": "blocking",
            "references": list(set(refs)),
        })

    # Extraire les contrôles SIG
    for m in SIG_RE.finditer(text):
        sig_id = m.group(1)
        rule_text = m.group(2).strip()
        start = m.end()
        remaining = text[start:]
        continuation_lines = []
        for rline in remaining.split("\n"):
            rstripped = rline.strip()
            if not rstripped:
                break
            if CCH_RE.match(rstripped) or SIG_RE.match(rstripped):
                break
            continuation_lines.append(rstripped)

        full_rule = rule_text + " " + " ".join(continuation_lines) if continuation_lines else rule_text

        rub.sig_controls.append({
            "id": sig_id,
            "rule_text": full_rule.strip()[:500],
            "severity": "warning",
        })

    # Extraire les énumérations
    enum_values = []
    for line in lines:
        m = ENUM_RE.match(line.strip())
        if m:
            enum_values.append({
                "code": m.group(1),
                "label": m.group(2).strip(),
            })

    if enum_values:
        rub.enumeration = enum_values

    return rub


def build_ct_json(blocs: dict[str, ExtractedBloc], version: str) -> dict:
    """Construit le JSON final du cahier technique."""
    return {
        "version": version,
        "extraction_date": "",
        "source_hash": "",
        "blocs": {k: v.to_dict() for k, v in sorted(blocs.items())},
    }


def main(pdf_path: str, output_dir: str, version: str = "CT2025.1") -> None:
    """Point d'entrée principal pour l'extraction."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    blocs = extract_from_pdf(pdf_path)

    # Sauvegarder le ct.json
    ct_data = build_ct_json(blocs, version)
    ct_path = output / "ct.json"
    with open(ct_path, "w", encoding="utf-8") as f:
        json.dump(ct_data, f, ensure_ascii=False, indent=2)

    logger.info("ct.json écrit : %s", ct_path)

    # Stats
    total_rub = sum(len(b.rubriques) for b in blocs.values())
    total_cch = sum(
        len(r.cch_controls) for b in blocs.values() for r in b.rubriques.values()
    )
    total_enum = sum(
        len(r.enumeration or []) for b in blocs.values() for r in b.rubriques.values()
    )

    print(f"\n=== Extraction terminée ===")
    print(f"Blocs : {len(blocs)}")
    print(f"Rubriques : {total_rub}")
    print(f"Contrôles CCH : {total_cch}")
    print(f"Valeurs d'énumération : {total_enum}")

    # Sauvegarder metadata
    metadata = {
        "ct_version": version,
        "norm_year": int(re.search(r"(\d{4})", version).group(1)) if re.search(r"(\d{4})", version) else 0,
        "publication_date": "",
        "extraction_date": "",
        "stats": {
            "total_blocs": len(blocs),
            "total_rubriques": total_rub,
            "total_cch_controls": total_cch,
            "total_enum_values": total_enum,
        },
    }
    meta_path = output / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.extract_pdf <pdf_path> <output_dir> [version]")
        sys.exit(1)
    version = sys.argv[3] if len(sys.argv) > 3 else "CT2025.1"
    main(sys.argv[1], sys.argv[2], version)

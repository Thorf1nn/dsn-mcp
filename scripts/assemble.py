"""Assemblage des données DSN : XLSX (source primaire) + PDF (enrichissement).

Le XLSX est la source de vérité pour :
- La structure des blocs et rubriques
- Les noms propres (labels, noms de blocs)
- Les types de données, longueurs, regex
- Les valeurs d'énumération
- Les contrôles CCH/SIG/CSL

Le PDF apporte en complément :
- Des descriptions parfois plus détaillées
- Des contrôles CCH supplémentaires (rares)

Usage :
    python -m scripts.assemble <xlsx_ct_json> <pdf_ct_json> <output_dir> [version]
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def assemble(xlsx_data: dict, pdf_data: dict | None = None) -> dict:
    """Assemble les données XLSX avec l'enrichissement PDF optionnel.

    Args:
        xlsx_data: Données extraites du XLSX (source primaire).
        pdf_data: Données extraites du PDF (enrichissement optionnel).

    Returns:
        Données assemblées.
    """
    if not pdf_data:
        logger.info("Pas de données PDF, utilisation du XLSX seul")
        return xlsx_data

    enriched = 0

    for bloc_code, bloc in xlsx_data["blocs"].items():
        pdf_bloc = pdf_data.get("blocs", {}).get(bloc_code)
        if not pdf_bloc:
            continue

        for rub_code, rub in bloc["rubriques"].items():
            pdf_rub = pdf_bloc.get("rubriques", {}).get(rub_code)
            if not pdf_rub:
                continue

            # Enrichir la description si le PDF est significativement plus long
            xlsx_desc = rub.get("description") or ""
            pdf_desc = pdf_rub.get("description") or ""
            if len(pdf_desc) > len(xlsx_desc) + 50:
                rub["description"] = pdf_desc
                enriched += 1

            # Ajouter les CCH du PDF absents du XLSX
            xlsx_cch_ids = {c["id"] for c in rub.get("cch_controls", [])}
            for cch in pdf_rub.get("cch_controls", []):
                if cch["id"] not in xlsx_cch_ids:
                    rub["cch_controls"].append(cch)
                    enriched += 1

    logger.info("Enrichissements depuis le PDF : %d", enriched)
    return xlsx_data


def main(xlsx_json_path: str, pdf_json_path: str | None, output_dir: str, version: str = "CT2026.1") -> None:
    """Point d'entrée pour l'assemblage."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Charger XLSX
    with open(xlsx_json_path, encoding="utf-8") as f:
        xlsx_data = json.load(f)

    # Charger PDF (optionnel)
    pdf_data = None
    if pdf_json_path and Path(pdf_json_path).exists():
        with open(pdf_json_path, encoding="utf-8") as f:
            pdf_data = json.load(f)

    # Assembler
    result = assemble(xlsx_data, pdf_data)

    # Mettre à jour la version
    result["version"] = version
    result["extraction_date"] = date.today().isoformat()

    # Sauvegarder
    ct_path = output / "ct.json"
    with open(ct_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Stats
    total_blocs = len(result["blocs"])
    total_rub = sum(len(b["rubriques"]) for b in result["blocs"].values())
    total_cch = sum(
        len(r["cch_controls"]) for b in result["blocs"].values() for r in b["rubriques"].values()
    )
    total_sig = sum(
        len(r["sig_controls"]) for b in result["blocs"].values() for r in b["rubriques"].values()
    )
    total_csl = sum(
        len(r["csl_controls"]) for b in result["blocs"].values() for r in b["rubriques"].values()
    )
    total_enum = sum(
        len(r["enumeration"] or []) for b in result["blocs"].values() for r in b["rubriques"].values()
    )

    print(f"\n=== Assemblage terminé ===")
    print(f"Blocs : {total_blocs}")
    print(f"Rubriques : {total_rub}")
    print(f"Contrôles CCH : {total_cch}")
    print(f"Contrôles SIG : {total_sig}")
    print(f"Contrôles CSL/CRE : {total_csl}")
    print(f"Valeurs d'énumération : {total_enum}")

    # Metadata
    norm_year = 0
    m = re.search(r"(\d{4})", version)
    if m:
        norm_year = int(m.group(1))

    metadata = {
        "ct_version": version,
        "norm_year": norm_year,
        "publication_date": "",
        "extraction_date": date.today().isoformat(),
        "sources": ["xlsx", "pdf"] if pdf_data else ["xlsx"],
        "stats": {
            "total_blocs": total_blocs,
            "total_rubriques": total_rub,
            "total_cch_controls": total_cch,
            "total_sig_controls": total_sig,
            "total_csl_controls": total_csl,
            "total_enum_values": total_enum,
        },
    }
    meta_path = output / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info("ct.json écrit : %s", ct_path)
    logger.info("metadata.json écrit : %s", meta_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.assemble <xlsx_ct_json> [pdf_ct_json] <output_dir> [version]")
        print("  pdf_ct_json peut être 'none' pour ignorer le PDF")
        sys.exit(1)

    xlsx_json = sys.argv[1]
    if len(sys.argv) >= 4:
        pdf_json = sys.argv[2] if sys.argv[2].lower() != "none" else None
        out_dir = sys.argv[3]
        ver = sys.argv[4] if len(sys.argv) > 4 else "CT2026.1"
    else:
        pdf_json = None
        out_dir = sys.argv[2]
        ver = sys.argv[3] if len(sys.argv) > 3 else "CT2026.1"

    main(xlsx_json, pdf_json, out_dir, ver)

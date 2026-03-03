from __future__ import annotations

from dsn_mcp.models import Bloc, CahierTechnique, EnumValue, Rubrique


def search_rubriques(ct: CahierTechnique, query: str, limit: int = 20) -> list[tuple[Bloc, Rubrique, int]]:
    """Recherche multi-champs avec scoring de pertinence.

    Retourne une liste de (bloc, rubrique, score) triée par score décroissant.
    """
    q = query.lower().strip()
    if not q:
        return []

    results: list[tuple[Bloc, Rubrique, int]] = []

    for bloc in ct.blocs.values():
        for rub in bloc.rubriques.values():
            score = _score_rubrique(rub, q)
            if score > 0:
                results.append((bloc, rub, score))

    results.sort(key=lambda x: -x[2])
    return results[:limit]


def _score_rubrique(rub: Rubrique, query: str) -> int:
    """Calcule un score de pertinence pour une rubrique."""
    # Code exact
    if query == rub.code.lower():
        return 100
    # Préfixe de code
    if rub.code.lower().startswith(query):
        return 80
    # Nom technique exact
    if rub.technical_name and query == rub.technical_name.lower():
        return 90
    # Nom technique contient
    if rub.technical_name and query in rub.technical_name.lower():
        return 60
    # Libellé contient
    if query in rub.label.lower():
        return 50
    # Valeur d'énumération
    if rub.enumeration and any(query in f"{e.code} {e.label}".lower() for e in rub.enumeration):
        return 30
    # Description contient
    if rub.description and query in rub.description.lower():
        return 20
    return 0


def search_enumerations(
    ct: CahierTechnique, query: str, limit: int = 20
) -> list[tuple[Bloc, Rubrique, EnumValue]]:
    """Recherche dans les valeurs d'énumération de toutes les rubriques."""
    q = query.lower().strip()
    if not q:
        return []

    results: list[tuple[Bloc, Rubrique, EnumValue]] = []

    for bloc in ct.blocs.values():
        for rub in bloc.rubriques.values():
            if not rub.enumeration:
                continue
            for ev in rub.enumeration:
                if q in ev.code.lower() or q in ev.label.lower():
                    results.append((bloc, rub, ev))

    return results[:limit]

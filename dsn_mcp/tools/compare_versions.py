from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_compare_versions_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def compare_versions(
        version_from: Annotated[str, Field(description="Version source (ex: '2025')")],
        version_to: Annotated[str, Field(description="Version cible (ex: '2026')")],
        bloc_code: Annotated[str | None, Field(description="Comparer un bloc spécifique")] = None,
        rubrique_code: Annotated[str | None, Field(description="Comparer une rubrique spécifique")] = None,
    ) -> str:
        """Compare deux versions du Cahier Technique DSN.
        Montre les ajouts, suppressions et modifications de blocs/rubriques."""
        try:
            v_from = store._resolve_version(version_from)
            v_to = store._resolve_version(version_to)
        except ValueError as e:
            return str(e)

        ct_from = store.versions[v_from]
        ct_to = store.versions[v_to]

        if rubrique_code:
            return _compare_rubrique(rubrique_code, ct_from, ct_to, v_from, v_to)
        if bloc_code:
            return _compare_bloc(bloc_code, ct_from, ct_to, v_from, v_to)
        return _compare_global(ct_from, ct_to, v_from, v_to)


def _compare_global(ct_from, ct_to, v_from: str, v_to: str) -> str:
    blocs_from = set(ct_from.blocs.keys())
    blocs_to = set(ct_to.blocs.keys())

    added = sorted(blocs_to - blocs_from)
    removed = sorted(blocs_from - blocs_to)
    common = sorted(blocs_from & blocs_to)

    lines = [f"# Comparaison CT{v_from} → CT{v_to}\n"]

    if added:
        lines.append(f"## Blocs ajoutés ({len(added)})")
        for b in added:
            lines.append(f"- **{b}** - {ct_to.blocs[b].name}")

    if removed:
        lines.append(f"\n## Blocs supprimés ({len(removed)})")
        for b in removed:
            lines.append(f"- **{b}** - {ct_from.blocs[b].name}")

    modified_blocs = []
    for b in common:
        rubs_from = set(ct_from.blocs[b].rubriques.keys())
        rubs_to = set(ct_to.blocs[b].rubriques.keys())
        if rubs_from != rubs_to:
            rub_added = rubs_to - rubs_from
            rub_removed = rubs_from - rubs_to
            modified_blocs.append((b, rub_added, rub_removed))

    if modified_blocs:
        lines.append(f"\n## Blocs modifiés ({len(modified_blocs)})")
        for b, rub_added, rub_removed in modified_blocs:
            lines.append(f"\n### {b} - {ct_to.blocs[b].name}")
            for r in sorted(rub_added):
                lines.append(f"  + {r} : {ct_to.blocs[b].rubriques[r].label}")
            for r in sorted(rub_removed):
                lines.append(f"  - {r} : {ct_from.blocs[b].rubriques[r].label}")

    if not added and not removed and not modified_blocs:
        lines.append("Aucune différence structurelle détectée au niveau des blocs et rubriques.")

    return "\n".join(lines)


def _compare_bloc(bloc_code: str, ct_from, ct_to, v_from: str, v_to: str) -> str:
    b_from = ct_from.blocs.get(bloc_code)
    b_to = ct_to.blocs.get(bloc_code)

    if not b_from and not b_to:
        return f"Bloc '{bloc_code}' non trouvé dans CT{v_from} ni CT{v_to}."
    if not b_from:
        return f"Bloc '{bloc_code}' ajouté dans CT{v_to} ({len(b_to.rubriques)} rubriques)."
    if not b_to:
        return f"Bloc '{bloc_code}' supprimé dans CT{v_to} (existait dans CT{v_from} avec {len(b_from.rubriques)} rubriques)."

    rubs_from = set(b_from.rubriques.keys())
    rubs_to = set(b_to.rubriques.keys())

    added = sorted(rubs_to - rubs_from)
    removed = sorted(rubs_from - rubs_to)

    lines = [f"# Comparaison du bloc {bloc_code} : CT{v_from} → CT{v_to}\n"]

    if added:
        lines.append(f"## Rubriques ajoutées ({len(added)})")
        for r in added:
            lines.append(f"- **{r}** : {b_to.rubriques[r].label}")

    if removed:
        lines.append(f"\n## Rubriques supprimées ({len(removed)})")
        for r in removed:
            lines.append(f"- **{r}** : {b_from.rubriques[r].label}")

    if not added and not removed:
        lines.append("Aucune différence de rubriques détectée.")

    return "\n".join(lines)


def _compare_rubrique(rubrique_code: str, ct_from, ct_to, v_from: str, v_to: str) -> str:
    rub_from = _find_rubrique(ct_from, rubrique_code)
    rub_to = _find_rubrique(ct_to, rubrique_code)

    if not rub_from and not rub_to:
        return f"Rubrique '{rubrique_code}' non trouvée dans CT{v_from} ni CT{v_to}."
    if not rub_from:
        return f"Rubrique '{rubrique_code}' ajoutée dans CT{v_to} : {rub_to.label}"
    if not rub_to:
        return f"Rubrique '{rubrique_code}' supprimée dans CT{v_to} (existait dans CT{v_from})"

    diffs = []
    if rub_from.label != rub_to.label:
        diffs.append(f"- Libellé : `{rub_from.label}` → `{rub_to.label}`")
    if rub_from.data_type != rub_to.data_type:
        diffs.append(f"- Type : `{rub_from.data_type}` → `{rub_to.data_type}`")
    if rub_from.length_max != rub_to.length_max or rub_from.length_min != rub_to.length_min:
        diffs.append(f"- Longueur : [{rub_from.length_min},{rub_from.length_max}] → [{rub_to.length_min},{rub_to.length_max}]")
    if rub_from.format_regex != rub_to.format_regex:
        diffs.append(f"- Format : `{rub_from.format_regex}` → `{rub_to.format_regex}`")

    enum_from = {e.code for e in (rub_from.enumeration or [])}
    enum_to = {e.code for e in (rub_to.enumeration or [])}
    if enum_from != enum_to:
        added_vals = enum_to - enum_from
        removed_vals = enum_from - enum_to
        if added_vals:
            diffs.append(f"- Valeurs ajoutées : {', '.join(sorted(added_vals))}")
        if removed_vals:
            diffs.append(f"- Valeurs supprimées : {', '.join(sorted(removed_vals))}")

    cch_from = len(rub_from.cch_controls)
    cch_to = len(rub_to.cch_controls)
    if cch_from != cch_to:
        diffs.append(f"- Contrôles CCH : {cch_from} → {cch_to}")

    lines = [f"# Comparaison de {rubrique_code} : CT{v_from} → CT{v_to}\n"]

    if diffs:
        lines.extend(diffs)
    else:
        lines.append("Aucune différence détectée.")

    return "\n".join(lines)


def _find_rubrique(ct, rubrique_code: str):
    parts = rubrique_code.rsplit(".", 1)
    if len(parts) == 2:
        bloc = ct.blocs.get(parts[0])
        if bloc:
            return bloc.rubriques.get(rubrique_code)
    for bloc in ct.blocs.values():
        if rubrique_code in bloc.rubriques:
            return bloc.rubriques[rubrique_code]
    return None

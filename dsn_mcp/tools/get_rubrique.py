from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_get_rubrique_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_rubrique(
        rubrique_code: Annotated[str, Field(description="Code complet de la rubrique, ex: 'S21.G00.40.007'")],
        version: Annotated[str | None, Field(description="Version du CT (ex: '2026'). Par défaut la plus récente.")] = None,
    ) -> str:
        """Détails complets d'une rubrique DSN : type, format, valeurs d'énumération,
        règles de validation (CCH, SIG, CSL). Utiliser search_rubriques pour trouver le code."""
        try:
            bloc, rub = store.get_rubrique(rubrique_code, version)
        except ValueError as e:
            return str(e)

        if not rub or not bloc:
            v = version or store.default_version
            return f"Rubrique '{rubrique_code}' non trouvée dans CT{v}."

        lines = [
            f"# {rub.code} - {rub.label}",
            f"Bloc : {bloc.code} ({bloc.name})",
            f"Nom technique : {rub.technical_name or 'N/A'}",
            f"Type : {rub.data_type} | Longueur : [{rub.length_min},{rub.length_max}]",
        ]

        if rub.format_regex:
            lines.append(f"Format (regex) : `{rub.format_regex}`")

        if rub.description:
            lines.append(f"\n{rub.description[:1000]}")

        if rub.enumeration:
            lines.append(f"\n**Valeurs ({len(rub.enumeration)}) :**")
            for ev in rub.enumeration:
                lines.append(f"  {ev.code} - {ev.label}")

        if rub.cch_controls:
            lines.append(f"\n**Contrôles CCH ({len(rub.cch_controls)}) :**")
            for c in rub.cch_controls:
                refs = f" (réf: {', '.join(c.references)})" if c.references else ""
                lines.append(f"  {c.id}: {c.rule_text[:300]}{refs}")

        if rub.sig_controls:
            lines.append(f"\n**Signalements SIG ({len(rub.sig_controls)}) :**")
            for s in rub.sig_controls:
                lines.append(f"  {s.id}: {s.rule_text[:300]}")

        if rub.csl_controls:
            lines.append(f"\n**Contrôles CSL ({len(rub.csl_controls)}) :**")
            for c in rub.csl_controls:
                lines.append(f"  {c.id}: `{c.pattern}` - {c.description}")

        return "\n".join(lines)

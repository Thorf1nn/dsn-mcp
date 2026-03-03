from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_get_nomenclature_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_nomenclature(
        table_name: Annotated[str, Field(description="Nom de la table de nomenclature (ex: 'IDCC', 'NAF', 'PCSESE'). Utiliser sans paramètre pour lister les tables disponibles.")],
        search: Annotated[str | None, Field(description="Filtrer les valeurs par code ou libellé")] = None,
        version: Annotated[str | None, Field(description="Version du CT. Par défaut la plus récente.")] = None,
        limit: Annotated[int, Field(description="Nombre max de valeurs à retourner", ge=1, le=100)] = 50,
    ) -> str:
        """Interroger les tables de nomenclature externes (IDCC, NAF, PCS-ESE, etc.).
        Ces tables contiennent les valeurs de référence pour certaines rubriques."""
        try:
            v = store._resolve_version(version)
        except ValueError as e:
            return str(e)

        if table_name.lower() == "list":
            tables = store.list_nomenclatures(v)
            if not tables:
                return f"Aucune table de nomenclature chargée pour CT{v}."
            lines = [f"# Tables de nomenclature disponibles (CT{v})\n"]
            for t in tables:
                nom = store.get_nomenclature(t, v)
                desc = f" - {nom.description}" if nom and nom.description else ""
                lines.append(f"- **{t}**{desc}")
            return "\n".join(lines)

        table = store.get_nomenclature(table_name, v)
        if not table:
            available = store.list_nomenclatures(v)
            return f"Table '{table_name}' non trouvée dans CT{v}. Tables disponibles : {', '.join(available)}"

        values = table.values
        if search:
            q = search.lower()
            values = [v for v in values if q in v.code.lower() or q in v.label.lower()]

        total = len(values)
        values = values[:limit]

        lines = [f"# {table.name}"]
        if table.description:
            lines.append(f"{table.description}\n")
        lines.append(f"**{total} valeur(s)** (affichage limité à {limit}) :\n")

        for v in values:
            lines.append(f"- {v.code} - {v.label}")

        return "\n".join(lines)

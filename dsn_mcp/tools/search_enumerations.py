from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.search import search_enumerations as do_search
from dsn_mcp.store import DSNDataStore


def register_search_enumerations_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def search_enumerations(
        query: Annotated[str, Field(description="Terme de recherche dans les valeurs d'énumération (code ou libellé)")],
        version: Annotated[str | None, Field(description="Version du CT. Par défaut la plus récente.")] = None,
        limit: Annotated[int, Field(description="Nombre max de résultats", ge=1, le=50)] = 20,
    ) -> str:
        """Recherche dans les valeurs d'énumération de toutes les rubriques DSN.
        Utile pour trouver quelle rubrique utilise un code spécifique."""
        try:
            v = store._resolve_version(version)
        except ValueError as e:
            return str(e)

        ct = store.versions[v]
        results = do_search(ct, query, limit)

        if not results:
            return f"Aucune valeur d'énumération trouvée pour '{query}' dans CT{v}."

        lines = [f"# Énumérations contenant '{query}' (CT{v}) - {len(results)} résultat(s)\n"]
        for bloc, rub, ev in results:
            lines.append(
                f"- **{ev.code} - {ev.label}**\n"
                f"  Rubrique : {rub.code} ({rub.label}) | Bloc : {bloc.code} ({bloc.name})"
            )

        return "\n".join(lines)

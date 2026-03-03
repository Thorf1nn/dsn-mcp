from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.search import search_rubriques as do_search
from dsn_mcp.store import DSNDataStore


def register_search_rubriques_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def search_rubriques(
        query: Annotated[str, Field(description="Terme de recherche : code rubrique (S21.G00.40.007), mot-clé du libellé, ou nom technique")],
        version: Annotated[str | None, Field(description="Version du CT (ex: '2026'). Par défaut la plus récente.")] = None,
        limit: Annotated[int, Field(description="Nombre max de résultats", ge=1, le=50)] = 20,
    ) -> str:
        """Recherche de rubriques DSN par code, libellé, nom technique ou mot-clé.
        Retourne les rubriques correspondantes avec leur bloc, code, libellé et type."""
        try:
            v = store._resolve_version(version)
        except ValueError as e:
            return str(e)

        ct = store.versions[v]
        results = do_search(ct, query, limit)

        if not results:
            return f"Aucune rubrique trouvée pour '{query}' dans CT{v}."

        lines = [f"# Résultats pour '{query}' (CT{v}) - {len(results)} résultat(s)\n"]
        for bloc, rub, score in results:
            enum_info = f" | {len(rub.enumeration)} valeurs" if rub.enumeration else ""
            lines.append(
                f"- **{rub.code}** - {rub.label}\n"
                f"  Bloc: {bloc.code} ({bloc.name}) | Type: {rub.data_type} [{rub.length_min},{rub.length_max}]{enum_info}"
            )

        return "\n".join(lines)

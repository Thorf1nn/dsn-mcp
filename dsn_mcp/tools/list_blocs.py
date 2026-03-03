from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_list_blocs_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def list_blocs(
        version: Annotated[str | None, Field(description="Version du CT (ex: '2026'). Par défaut la plus récente.")] = None,
    ) -> str:
        """Liste tous les blocs DSN avec leur code et nom.
        Un bloc est un objet métier regroupant des rubriques (ex: Contrat, Individu, Rémunération)."""
        try:
            blocs = store.list_blocs(version)
        except ValueError as e:
            return str(e)

        if not blocs:
            return "Aucun bloc trouvé."

        v = version or store.default_version
        lines = [f"# Blocs DSN (CT{v}) - {len(blocs)} blocs\n"]
        for bloc in blocs:
            rub_count = len(bloc.rubriques)
            lines.append(f"- **{bloc.code}** - {bloc.name} ({rub_count} rubriques)")

        return "\n".join(lines)

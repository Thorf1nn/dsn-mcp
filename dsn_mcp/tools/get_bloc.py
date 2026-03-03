from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_get_bloc_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_bloc(
        bloc_code: Annotated[str, Field(description="Code du bloc, ex: 'S21.G00.40' pour Contrat")],
        version: Annotated[str | None, Field(description="Version du CT (ex: '2026'). Par défaut la plus récente.")] = None,
    ) -> str:
        """Détails complets d'un bloc DSN avec la liste de toutes ses rubriques.
        Un bloc est un objet métier (ex: S21.G00.40 = Contrat, S21.G00.30 = Individu)."""
        try:
            bloc = store.get_bloc(bloc_code, version)
        except ValueError as e:
            return str(e)

        if not bloc:
            v = version or store.default_version
            return f"Bloc '{bloc_code}' non trouvé dans CT{v}."

        lines = [f"# {bloc.code} - {bloc.name}\n"]

        if bloc.description:
            desc = bloc.description[:600]
            lines.append(f"{desc}\n")

        if bloc.parent_bloc:
            lines.append(f"Bloc parent : {bloc.parent_bloc}\n")

        lines.append(f"**{len(bloc.rubriques)} rubriques :**\n")

        for code in sorted(bloc.rubriques):
            rub = bloc.rubriques[code]
            extras = []
            if rub.enumeration:
                extras.append(f"{len(rub.enumeration)} valeurs")
            if rub.cch_controls:
                extras.append(f"{len(rub.cch_controls)} CCH")
            suffix = f" ({', '.join(extras)})" if extras else ""
            lines.append(f"- `{code}` : {rub.label} [{rub.data_type}]{suffix}")

        return "\n".join(lines)

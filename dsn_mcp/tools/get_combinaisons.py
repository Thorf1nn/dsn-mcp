from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_get_combinaisons_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_combinaisons(
        bloc_code: Annotated[str, Field(description="Code du bloc, ex: 'S21.G00.82' pour Cotisation établissement")],
        version: Annotated[str | None, Field(description="Version du CT. Par défaut la plus récente.")] = None,
    ) -> str:
        """Combinaisons valides de codes pour un bloc DSN.
        Certains blocs n'autorisent que certaines combinaisons de valeurs."""
        try:
            combinaisons = store.get_combinaisons(bloc_code, version)
        except ValueError as e:
            return str(e)

        v = version or store.default_version

        if not combinaisons:
            return f"Aucune règle de combinaison trouvée pour le bloc '{bloc_code}' dans CT{v}."

        lines = [f"# Combinaisons valides pour {bloc_code} (CT{v})\n"]

        for combo in combinaisons:
            lines.append(f"## {combo.description}\n")
            lines.append(f"Champs concernés : {', '.join(combo.fields)}\n")

            if combo.valid_combinations:
                headers = list(combo.valid_combinations[0].keys())
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join("---" for _ in headers) + " |")
                for vc in combo.valid_combinations:
                    lines.append("| " + " | ".join(vc.get(h, "") for h in headers) + " |")

            lines.append("")

        return "\n".join(lines)

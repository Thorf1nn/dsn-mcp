from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.models import DECLARATION_MODELS
from dsn_mcp.store import DSNDataStore


def register_get_usage_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_usage(
        rubrique_code: Annotated[str, Field(description="Code de la rubrique, ex: 'S21.G00.40.007'")],
        version: Annotated[str | None, Field(description="Version du CT (ex: '2026'). Par défaut la plus récente.")] = None,
    ) -> str:
        """Statut d'usage d'une rubrique par modèle de déclaration.
        O=Obligatoire, C=Conditionnel, F=Facultatif, I=Interdit, N=Non applicable."""
        try:
            usage = store.get_usage(rubrique_code, version)
        except ValueError as e:
            return str(e)

        v = version or store.default_version

        if not usage:
            return f"Pas de données d'usage pour '{rubrique_code}' dans CT{v}."

        _, rub = store.get_rubrique(rubrique_code, version)
        label = rub.label if rub else rubrique_code

        lines = [f"# Usage de {rubrique_code} - {label}\n"]
        lines.append("| Modèle | Code | Statut |")
        lines.append("|--------|------|--------|")

        status_map = {
            "O": "Obligatoire",
            "C": "Conditionnel",
            "F": "Facultatif",
            "I": "Interdit",
            "N": "Non applicable",
        }

        for model_code, model_name in DECLARATION_MODELS.items():
            field = f"model_{model_code}"
            val = getattr(usage, field, None)
            if val:
                status = status_map.get(val, val)
                lines.append(f"| {model_name} | {model_code} | **{val}** - {status} |")

        return "\n".join(lines)

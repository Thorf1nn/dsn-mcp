from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dsn_mcp.store import DSNDataStore


def register_get_controls_tool(mcp: FastMCP, store: DSNDataStore) -> None:
    @mcp.tool()
    async def get_controls(
        code: Annotated[str, Field(description="Code rubrique (ex: 'S21.G00.40.007') ou code bloc (ex: 'S21.G00.40')")],
        control_type: Annotated[str | None, Field(description="Filtrer par type : 'cch' (bloquant), 'sig' (signal), 'csl' (format). Tous par défaut.")] = None,
        version: Annotated[str | None, Field(description="Version du CT. Par défaut la plus récente.")] = None,
    ) -> str:
        """Tous les contrôles de validation pour une rubrique ou un bloc entier.
        CCH = bloquant, SIG = signal non-bloquant, CSL = format."""
        try:
            controls = store.get_controls(code, control_type, version)
        except ValueError as e:
            return str(e)

        total = sum(len(v) for v in controls.values())
        if total == 0:
            v = version or store.default_version
            return f"Aucun contrôle trouvé pour '{code}' dans CT{v}."

        lines = [f"# Contrôles pour {code}\n"]

        if controls["cch"]:
            lines.append(f"## CCH - Contrôles bloquants ({len(controls['cch'])})\n")
            for c in controls["cch"]:
                refs = f"\n  Références : {', '.join(c.references)}" if c.references else ""
                lines.append(f"- **{c.id}** : {c.rule_text[:400]}{refs}\n")

        if controls["sig"]:
            lines.append(f"## SIG - Signalements ({len(controls['sig'])})\n")
            for s in controls["sig"]:
                lines.append(f"- **{s.id}** : {s.rule_text[:400]}\n")

        if controls["csl"]:
            lines.append(f"## CSL - Contrôles de format ({len(controls['csl'])})\n")
            for c in controls["csl"]:
                lines.append(f"- **{c.id}** : `{c.pattern}` - {c.description}\n")

        return "\n".join(lines)

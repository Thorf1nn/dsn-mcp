from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from dsn_mcp.store import DSNDataStore

from dsn_mcp.tools.list_blocs import register_list_blocs_tool
from dsn_mcp.tools.get_bloc import register_get_bloc_tool
from dsn_mcp.tools.search_rubriques import register_search_rubriques_tool
from dsn_mcp.tools.get_rubrique import register_get_rubrique_tool
from dsn_mcp.tools.get_usage import register_get_usage_tool
from dsn_mcp.tools.get_controls import register_get_controls_tool
from dsn_mcp.tools.search_enumerations import register_search_enumerations_tool
from dsn_mcp.tools.get_combinaisons import register_get_combinaisons_tool
from dsn_mcp.tools.get_nomenclature import register_get_nomenclature_tool
from dsn_mcp.tools.compare_versions import register_compare_versions_tool


def register_tools(mcp: FastMCP, store: DSNDataStore) -> None:
    register_list_blocs_tool(mcp, store)
    register_get_bloc_tool(mcp, store)
    register_search_rubriques_tool(mcp, store)
    register_get_rubrique_tool(mcp, store)
    register_get_usage_tool(mcp, store)
    register_get_controls_tool(mcp, store)
    register_search_enumerations_tool(mcp, store)
    register_get_combinaisons_tool(mcp, store)
    register_get_nomenclature_tool(mcp, store)
    register_compare_versions_tool(mcp, store)

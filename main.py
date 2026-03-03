from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dsn_mcp.store import DSNDataStore
from dsn_mcp.tools import register_tools

log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Charger les données pré-parsées
data_dir = Path(__file__).parent / "data"
default_version = os.getenv("DSN_DEFAULT_VERSION", "")

store = DSNDataStore()
store.load_all_versions(data_dir, default_version or None)

# Initialiser le serveur MCP
mcp = FastMCP(
    "DSN Cahier Technique",
    instructions=(
        "Ce serveur MCP donne accès au Cahier Technique de la DSN (Déclaration Sociale Nominative), "
        "la norme NEODeS qui définit les règles de constitution des déclarations sociales en France. "
        "Utilisez les outils disponibles pour rechercher des rubriques, consulter les détails des blocs, "
        "vérifier les règles de validation (CCH/SIG/CSL), et comparer les versions du cahier technique."
    ),
)

# Enregistrer les outils
register_tools(mcp, store)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.getenv("MCP_PORT", "8000"))
        host = os.getenv("MCP_HOST", "0.0.0.0")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")

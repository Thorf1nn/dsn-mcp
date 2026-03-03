#!/usr/bin/env bash
# ============================================================================
# DSN MCP Server - Script d'installation
# Compatible : Linux, macOS, Git Bash (Windows)
# ============================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERREUR]${NC} $1"; }

echo ""
echo "============================================"
echo "  DSN MCP Server - Installation"
echo "============================================"
echo ""

# --- Se placer dans le dossier du script ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Dossier du projet : $SCRIPT_DIR"

# --- Détecter l'OS ---
OS="linux"
VENV_PYTHON=".venv/bin/python"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
    VENV_PYTHON=".venv/Scripts/python.exe"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
fi
info "Système détecté : $OS"

# --- Trouver Python 3.13+ ---
PYTHON=""
for cmd in python3.13 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [[ "$major" -ge 3 && "$minor" -ge 13 ]]; then
            PYTHON="$cmd"
            ok "Python trouvé : $cmd (v$version)"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    error "Python 3.13+ est requis mais n'a pas été trouvé."
    echo "  Téléchargez Python : https://www.python.org/downloads/"
    exit 1
fi

# --- Créer l'environnement virtuel ---
if [[ -d ".venv" ]]; then
    ok "Environnement virtuel existant trouvé"
else
    info "Création de l'environnement virtuel..."
    if command -v uv &>/dev/null; then
        uv venv .venv --python "$PYTHON" --seed
        ok "Environnement créé avec uv"
    else
        "$PYTHON" -m venv .venv
        ok "Environnement créé avec venv"
    fi
fi

# --- Vérifier que le Python du venv existe ---
if [[ ! -f "$VENV_PYTHON" ]]; then
    error "Python du venv introuvable : $VENV_PYTHON"
    exit 1
fi

# --- Installer les dépendances ---
info "Installation des dépendances..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet -e .
ok "Dépendances installées"

# --- Vérifier les données ---
if [[ -f "data/2026/ct.json" ]]; then
    ok "Données CT2026 trouvées"
else
    warn "Données CT2026 non trouvées dans data/2026/ct.json"
    warn "Le serveur ne pourra pas démarrer sans données."
fi

# --- Résoudre les chemins absolus ---
if [[ "$OS" == "windows" ]]; then
    # Utiliser Python pour obtenir le chemin Windows natif (fiable)
    read -r PYTHON_PATH MAIN_PATH <<< "$("$VENV_PYTHON" -c "
import sys, pathlib
base = pathlib.Path('.').resolve()
py = base / '.venv' / 'Scripts' / 'python.exe'
main = base / 'main.py'
print(str(py), str(main))
")"
    # Chemin Claude Desktop config
    CLAUDE_DESKTOP_CONFIG="$APPDATA/Claude/claude_desktop_config.json"
else
    ABS_DIR="$SCRIPT_DIR"
    PYTHON_PATH="${ABS_DIR}/${VENV_PYTHON}"
    MAIN_PATH="${ABS_DIR}/main.py"
    # Chemin Claude Desktop config
    if [[ "$OS" == "macos" ]]; then
        CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    else
        CLAUDE_DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
    fi
fi

echo ""
echo "============================================"
echo "  Configuration MCP"
echo "============================================"
echo ""

# --- Configurer Claude Code ---
read -rp "Configurer Claude Code (fichier .mcp.json local) ? [O/n] " choice
choice=${choice:-O}
if [[ "$choice" =~ ^[OoYy]$ ]]; then
    "$VENV_PYTHON" -c "
import json, sys
config = {'mcpServers': {'dsn': {'command': sys.argv[1], 'args': [sys.argv[2]]}}}
with open('.mcp.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
" "$PYTHON_PATH" "$MAIN_PATH"
    ok "Claude Code configuré (.mcp.json créé)"
    info "Relancez Claude Code depuis ce dossier pour activer le MCP."
fi

# --- Configurer Claude Desktop ---
read -rp "Configurer Claude Desktop ? [O/n] " choice
choice=${choice:-O}
if [[ "$choice" =~ ^[OoYy]$ ]]; then
    if [[ -f "$CLAUDE_DESKTOP_CONFIG" ]]; then
        # Vérifier si dsn est déjà configuré
        if grep -q '"dsn"' "$CLAUDE_DESKTOP_CONFIG" 2>/dev/null; then
            warn "Une entrée 'dsn' existe déjà dans Claude Desktop. Pas de modification."
        else
            # Injecter l'entrée dsn dans mcpServers avec Python (fiable pour le JSON)
            "$VENV_PYTHON" -c "
import json, sys
config_path = sys.argv[1]
python_path = sys.argv[2]
main_path = sys.argv[3]
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
if 'mcpServers' not in config:
    config['mcpServers'] = {}
config['mcpServers']['dsn'] = {
    'command': python_path,
    'args': [main_path]
}
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
print('OK')
" "$CLAUDE_DESKTOP_CONFIG" "$PYTHON_PATH" "$MAIN_PATH"
            ok "Claude Desktop configuré"
            info "Redémarrez Claude Desktop pour activer le MCP."
        fi
    else
        # Créer le fichier de config
        mkdir -p "$(dirname "$CLAUDE_DESKTOP_CONFIG")"
        "$VENV_PYTHON" -c "
import json, sys
config = {'mcpServers': {'dsn': {'command': sys.argv[1], 'args': [sys.argv[2]]}}}
with open(sys.argv[3], 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
" "$PYTHON_PATH" "$MAIN_PATH" "$CLAUDE_DESKTOP_CONFIG"
        ok "Claude Desktop configuré (fichier créé)"
        info "Redémarrez Claude Desktop pour activer le MCP."
    fi
fi

# --- Test de lancement ---
echo ""
info "Test de lancement du serveur..."
if timeout 3 "$VENV_PYTHON" -c "
from dsn_mcp.store import DSNDataStore
from pathlib import Path
store = DSNDataStore()
store.load_all_versions(Path('data'))
blocs = store.list_blocs()
print(f'  Versions chargées : {len(store.list_versions())}')
print(f'  Blocs disponibles : {len(blocs)}')
rubriques = sum(len(b.rubriques) for b in blocs)
print(f'  Rubriques totales : {rubriques}')
" 2>/dev/null; then
    ok "Serveur opérationnel !"
else
    warn "Le test de lancement a échoué. Vérifiez les données dans data/"
fi

echo ""
echo "============================================"
echo -e "  ${GREEN}Installation terminée !${NC}"
echo "============================================"
echo ""
echo "Pour tester, demandez à Claude :"
echo "  \"Quelles sont les valeurs possibles pour la nature du contrat ?\""
echo "  \"Liste-moi tous les blocs de la DSN\""
echo "  \"Quelles différences entre CT2025 et CT2026 ?\""
echo ""

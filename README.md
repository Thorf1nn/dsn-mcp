# DSN MCP Server

Serveur [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) pour interroger le **Cahier Technique de la DSN** (Déclaration Sociale Nominative, norme NEODeS).

Permet à un LLM (Claude, etc.) de rechercher des rubriques, consulter les règles de validation, comparer les versions du cahier technique — sans avoir à fouiller dans un PDF de 380 pages.

## Installation rapide

**Prérequis** : [Python 3.13+](https://www.python.org/downloads/)

### Windows (PowerShell ou CMD)

```bat
git clone <url-du-repo> dsn-mcp
cd dsn-mcp
install.bat
```

### Linux / macOS / Git Bash

```bash
git clone <url-du-repo> dsn-mcp
cd dsn-mcp
chmod +x install.sh
./install.sh
```

Le script d'installation :
1. Crée un environnement virtuel Python
2. Installe les dépendances
3. Propose de configurer automatiquement **Claude Code** et/ou **Claude Desktop**

## Installation manuelle

```bash
# 1. Cloner le repo
git clone <url-du-repo> dsn-mcp
cd dsn-mcp

# 2. Créer l'environnement virtuel
python -m venv .venv

# 3. Activer l'environnement
# Windows :
.venv\Scripts\activate
# Linux/macOS :
source .venv/bin/activate

# 4. Installer les dépendances
pip install -e .
```

Puis configurer manuellement le MCP (voir section [Configuration](#configuration)).

## Configuration

### Claude Code

Créer un fichier `.mcp.json` à la racine du projet :

```json
{
  "mcpServers": {
    "dsn": {
      "command": "/chemin/absolu/vers/dsn-mcp/.venv/bin/python",
      "args": ["/chemin/absolu/vers/dsn-mcp/main.py"]
    }
  }
}
```

> Sur Windows, remplacer par `.venv\\Scripts\\python.exe` et utiliser des `\\` dans les chemins.

### Claude Desktop

Ajouter dans le fichier de configuration Claude Desktop :
- Windows : `%APPDATA%\Claude\claude_desktop_config.json`
- macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dsn": {
      "command": "/chemin/absolu/vers/dsn-mcp/.venv/bin/python",
      "args": ["/chemin/absolu/vers/dsn-mcp/main.py"]
    }
  }
}
```

Redémarrer Claude Desktop après modification.

## Outils disponibles

| Outil | Description |
|-------|-------------|
| `list_blocs` | Liste tous les blocs DSN avec code et nom |
| `get_bloc` | Détails complets d'un bloc avec la liste de ses rubriques |
| `search_rubriques` | Recherche de rubriques par code, libellé ou mot-clé |
| `get_rubrique` | Détails d'une rubrique : type, format, énumérations, contrôles |
| `get_usage` | Statut d'usage par modèle de déclaration (O/C/F/I/N) |
| `get_controls` | Contrôles de validation CCH (bloquant), SIG (signal), CSL (format) |
| `search_enumerations` | Recherche dans les valeurs d'énumération de toutes les rubriques |
| `get_combinaisons` | Combinaisons valides de codes pour un bloc |
| `get_nomenclature` | Tables de nomenclature externes (IDCC, NAF, PCS-ESE, etc.) |
| `compare_versions` | Différences entre deux versions du Cahier Technique |

Tous les outils acceptent un paramètre `version` optionnel (ex: `"2025"`, `"2026"`). Par défaut, la version la plus récente est utilisée.

## Exemples de prompts

Une fois le MCP configuré, essayez ces requêtes avec Claude :

- **"Quelles sont les valeurs possibles pour la nature du contrat ?"**
- **"Liste-moi tous les blocs de la DSN"**
- **"Quels contrôles CCH s'appliquent au bloc Contrat ?"**
- **"Cherche la rubrique date de début"**
- **"Quelles différences entre CT2025 et CT2026 pour le bloc Contrat ?"**
- **"Quel est le format attendu pour le NIR ?"**

## Versions du Cahier Technique

Les données pré-extraites sont incluses dans le repo :

| Version | Blocs | Rubriques | CCH | Énumérations |
|---------|-------|-----------|-----|-------------|
| CT2025 | 62 | 570 | 596 | 1606 |
| CT2026 | 62 | 573 | 622 | 1639 |

## Structure du projet

```
dsn-mcp/
├── main.py                  # Point d'entrée du serveur MCP
├── pyproject.toml            # Dépendances et configuration
├── install.sh                # Script d'installation Linux/macOS
├── install.bat               # Script d'installation Windows
├── data/
│   ├── 2025/                 # Données CT2025 (JSON pré-parsés)
│   └── 2026/                 # Données CT2026
├── dsn_mcp/
│   ├── models.py             # Modèles Pydantic (Bloc, Rubrique, etc.)
│   ├── store.py              # Chargement et requêtage des données
│   ├── search.py             # Moteur de recherche multi-champs
│   └── tools/                # 10 outils MCP
├── scripts/                  # Pipeline d'extraction (offline)
│   ├── extract_xlsx.py       # Parser XLSX (source primaire)
│   ├── extract_pdf.py        # Parser PDF (enrichissement)
│   └── assemble.py           # Assemblage XLSX + PDF
└── tests/                    # Tests unitaires
```

## Développement

### Prérequis développement

```bash
pip install -e ".[dev,extraction]"
```

### Lancer les tests

```bash
pytest tests/ -v
```

### Re-extraire les données

Si vous avez un nouveau Cahier Technique (PDF + XLSX depuis [net-entreprises.fr](https://www.net-entreprises.fr/)) :

```bash
# 1. Placer les fichiers dans data/sources/
#    - dsn-datatypes-CT{year}.xlsx
#    - dsn-cahier-technique-{year}.1.pdf

# 2. Extraire depuis le XLSX (source primaire)
python -m scripts.extract_xlsx data/sources/dsn-datatypes-CT2027.xlsx data/2027-xlsx CT2027.1

# 3. Extraire depuis le PDF (enrichissement)
python -m scripts.extract_pdf data/sources/dsn-cahier-technique-2027.1.pdf data/2027-pdf CT2027.1

# 4. Assembler les deux sources
python -m scripts.assemble data/2027-xlsx/ct.json data/2027-pdf/ct.json data/2027 CT2027.1

# 5. Vérifier
pytest tests/ -v
```

### Transport HTTP

Par défaut le serveur utilise le transport stdio. Pour le mode HTTP :

```bash
MCP_TRANSPORT=http MCP_PORT=8000 python main.py
```

## Licence

Usage interne.

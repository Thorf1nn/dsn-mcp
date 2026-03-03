@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================================
:: DSN MCP Server - Script d'installation Windows
:: ============================================================================

echo.
echo ============================================
echo   DSN MCP Server - Installation
echo ============================================
echo.

:: --- Se placer dans le dossier du script ---
cd /d "%~dp0"
echo [INFO] Dossier du projet : %CD%

:: --- Trouver Python 3.13+ ---
set "PYTHON="

:: Essayer python3 d'abord, puis python
for %%P in (python3 python) do (
    if not defined PYTHON (
        where %%P >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=*" %%V in ('%%P -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
                set "PYVER=%%V"
            )
            for /f "tokens=1,2 delims=." %%A in ("!PYVER!") do (
                if %%A geq 3 if %%B geq 13 (
                    set "PYTHON=%%P"
                    echo [OK] Python trouve : %%P ^(v!PYVER!^)
                )
            )
        )
    )
)

if not defined PYTHON (
    echo [ERREUR] Python 3.13+ est requis mais n'a pas ete trouve.
    echo   Telechargez Python : https://www.python.org/downloads/
    pause
    exit /b 1
)

:: --- Créer l'environnement virtuel ---
if exist ".venv\Scripts\python.exe" (
    echo [OK] Environnement virtuel existant trouve
) else (
    echo [INFO] Creation de l'environnement virtuel...
    where uv >nul 2>&1
    if !errorlevel! equ 0 (
        uv venv .venv --python %PYTHON% --seed
        echo [OK] Environnement cree avec uv
    ) else (
        %PYTHON% -m venv .venv
        echo [OK] Environnement cree avec venv
    )
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [ERREUR] Python du venv introuvable : %VENV_PYTHON%
    pause
    exit /b 1
)

:: --- Installer les dépendances ---
echo [INFO] Installation des dependances...
"%VENV_PYTHON%" -m pip install --quiet --upgrade pip
"%VENV_PYTHON%" -m pip install --quiet -e .
echo [OK] Dependances installees

:: --- Vérifier les données ---
if exist "data\2026\ct.json" (
    echo [OK] Donnees CT2026 trouvees
) else (
    echo [WARN] Donnees CT2026 non trouvees dans data\2026\ct.json
    echo [WARN] Le serveur ne pourra pas demarrer sans donnees.
)

:: --- Chemins absolus pour la config MCP ---
set "ABS_PYTHON=%VENV_PYTHON%"
set "ABS_MAIN=%CD%\main.py"

:: Échapper les backslashes pour JSON
set "JSON_PYTHON=%ABS_PYTHON:\=\\%"
set "JSON_MAIN=%ABS_MAIN:\=\\%"

echo.
echo ============================================
echo   Configuration MCP
echo ============================================
echo.

:: --- Configurer Claude Code ---
set /p "CC_CHOICE=Configurer Claude Code (fichier .mcp.json local) ? [O/n] "
if not defined CC_CHOICE set "CC_CHOICE=O"
if /i "%CC_CHOICE%"=="O" (
    (
        echo {
        echo   "mcpServers": {
        echo     "dsn": {
        echo       "command": "%JSON_PYTHON%",
        echo       "args": ["%JSON_MAIN%"]
        echo     }
        echo   }
        echo }
    ) > .mcp.json
    echo [OK] Claude Code configure ^(.mcp.json cree^)
    echo [INFO] Relancez Claude Code depuis ce dossier pour activer le MCP.
)
if /i "%CC_CHOICE%"=="Y" (
    (
        echo {
        echo   "mcpServers": {
        echo     "dsn": {
        echo       "command": "%JSON_PYTHON%",
        echo       "args": ["%JSON_MAIN%"]
        echo     }
        echo   }
        echo }
    ) > .mcp.json
    echo [OK] Claude Code configure ^(.mcp.json cree^)
    echo [INFO] Relancez Claude Code depuis ce dossier pour activer le MCP.
)

:: --- Configurer Claude Desktop ---
set "CLAUDE_CONFIG=%APPDATA%\Claude\claude_desktop_config.json"

set /p "CD_CHOICE=Configurer Claude Desktop ? [O/n] "
if not defined CD_CHOICE set "CD_CHOICE=O"
if /i "%CD_CHOICE%"=="O" goto :config_desktop
if /i "%CD_CHOICE%"=="Y" goto :config_desktop
goto :skip_desktop

:config_desktop
if exist "%CLAUDE_CONFIG%" (
    findstr /c:"\"dsn\"" "%CLAUDE_CONFIG%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [WARN] Une entree 'dsn' existe deja dans Claude Desktop. Pas de modification.
    ) else (
        "%VENV_PYTHON%" -c "import json,sys;c=json.load(open(sys.argv[1],'r',encoding='utf-8'));c.setdefault('mcpServers',{})['dsn']={'command':sys.argv[2],'args':[sys.argv[3]]};json.dump(c,open(sys.argv[1],'w',encoding='utf-8'),indent=2,ensure_ascii=False)" "%CLAUDE_CONFIG%" "%ABS_PYTHON%" "%ABS_MAIN%"
        echo [OK] Claude Desktop configure
        echo [INFO] Redemarrez Claude Desktop pour activer le MCP.
    )
) else (
    if not exist "%APPDATA%\Claude" mkdir "%APPDATA%\Claude"
    "%VENV_PYTHON%" -c "import json,sys;json.dump({'mcpServers':{'dsn':{'command':sys.argv[1],'args':[sys.argv[2]]}}},open(sys.argv[3],'w',encoding='utf-8'),indent=2,ensure_ascii=False)" "%ABS_PYTHON%" "%ABS_MAIN%" "%CLAUDE_CONFIG%"
    echo [OK] Claude Desktop configure ^(fichier cree^)
    echo [INFO] Redemarrez Claude Desktop pour activer le MCP.
)

:skip_desktop

:: --- Test de lancement ---
echo.
echo [INFO] Test de lancement du serveur...
"%VENV_PYTHON%" -c "from dsn_mcp.store import DSNDataStore;from pathlib import Path;s=DSNDataStore();s.load_all_versions(Path('data'));b=s.list_blocs();print(f'  Versions chargees : {len(s.list_versions())}');print(f'  Blocs disponibles : {len(b)}');print(f'  Rubriques totales : {sum(len(x.rubriques) for x in b)}')"
if %errorlevel% equ 0 (
    echo [OK] Serveur operationnel !
) else (
    echo [WARN] Le test de lancement a echoue. Verifiez les donnees dans data\
)

echo.
echo ============================================
echo   Installation terminee !
echo ============================================
echo.
echo Pour tester, demandez a Claude :
echo   "Quelles sont les valeurs possibles pour la nature du contrat ?"
echo   "Liste-moi tous les blocs de la DSN"
echo   "Quelles differences entre CT2025 et CT2026 ?"
echo.
pause

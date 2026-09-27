#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
DIST_DIR="$PROJECT_DIR/dist"
APP_PATH="$DIST_DIR/AMMDF.app"
DMG_PATH="$DIST_DIR/AMMDF-macOS.dmg"

cd "$PROJECT_DIR"

if [[ ! -x "$PYTHON" ]]; then
    if command -v python3.12 >/dev/null 2>&1; then
        python3.12 -m venv "$VENV_DIR"
    else
        printf '%s\n' "Python 3.12 est requis. Installez-le avec : brew install python@3.12 python-tk@3.12" >&2
        exit 1
    fi
fi

if ! "$PYTHON" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 11) and tkinter.TkVersion >= 8.6 else 1)'; then
    printf '%s\n' "Le venv doit utiliser Python 3.11+ avec Tk 8.6+. Recréez .venv avec Python 3.12." >&2
    exit 1
fi

printf '%s\n' "Installation des dépendances de build..."
"$PYTHON" -m pip install -r requirements-build.txt

printf '%s\n' "Compilation de AMMDF.app..."
"$PYTHON" -m PyInstaller --noconfirm --clean AMMDF.spec

if [[ ! -d "$APP_PATH" ]]; then
    printf 'Bundle introuvable : %s\n' "$APP_PATH" >&2
    exit 1
fi

DMG_STAGE="$(mktemp -d "${TMPDIR:-/tmp}/amm-dmg.XXXXXX")"
trap 'rm -rf "$DMG_STAGE"' EXIT
cp -R "$APP_PATH" "$DMG_STAGE/AMMDF.app"
ln -s /Applications "$DMG_STAGE/Applications"
mkdir -p "$DIST_DIR"

printf '%s\n' "Création de l’image disque..."
hdiutil create \
    -volname "AMMDF" \
    -srcfolder "$DMG_STAGE" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

printf '\nApplication : %s\nDMG : %s\n' "$APP_PATH" "$DMG_PATH"

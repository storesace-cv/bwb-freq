#!/usr/bin/env bash
# my-launcher.sh — automático e silencioso; só erros reais.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 0) Python do venv (obrigatório)
if [[ ! -x ".venv/bin/python" ]]; then
  echo "❌ Não encontrei .venv/bin/python. Cria e ativa o venv primeiro." >&2
  echo "   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
PYBIN=".venv/bin/python"

# 1) Limpar ambiente Qt ruidoso
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH QT_DEBUG_PLUGINS
export QT_QPA_PLATFORM="cocoa"
export QT_LOGGING_RULES="qt.*=false"
export QT_MAC_WANTS_LAYER=1

# 2) Garantir PySide6 (instala 6.7.3 se faltar; define BWB_FORCE_PYSIDE6_673=1 para forçar)
if [[ "${BWB_FORCE_PYSIDE6_673:-0}" == "1" ]]; then
  "$PYBIN" -m pip install -q "PySide6==6.7.3"
else
  if ! "$PYBIN" - >/dev/null 2>&1 <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    "$PYBIN" -m pip install -q "PySide6==6.7.3"
  fi
fi

# 3) Descobrir paths de plugins via Qt (robusto)
QT_INFO="$("$PYBIN" <<'PY'
import pathlib
import PySide6
from PySide6.QtCore import QLibraryInfo
base = pathlib.Path(PySide6.__file__).resolve().parent
plugins_root = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
if not plugins_root.exists():
    plugins_root = base/"Qt"/"plugins"
platforms = plugins_root/"platforms"
print(plugins_root)
print(platforms)
print(base)
PY
)"
QT_PLUGINS_ROOT="$(echo "$QT_INFO" | sed -n '1p')"
QT_PLATFORMS_DIR="$(echo "$QT_INFO" | sed -n '2p')"
PYSIDE_DIR="$(echo "$QT_INFO" | sed -n '3p')"

if [[ -z "$QT_PLUGINS_ROOT" || -z "$QT_PLATFORMS_DIR" || ! -d "$QT_PLATFORMS_DIR" ]]; then
  echo "❌ PySide6 encontrado, mas diretório de plugins inválido: '$QT_PLUGINS_ROOT' / '$QT_PLATFORMS_DIR'." >&2
  exit 1
fi

# 4) Remover quarentena (best-effort; silencioso)
xattr -r -d com.apple.quarantine "$PYSIDE_DIR" >/dev/null 2>&1 || true

# 5) Exportar paths corretos
export QT_PLUGIN_PATH="$QT_PLUGINS_ROOT"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLATFORMS_DIR"

# 6) Smoke test (como tu fizeste manualmente)
if ! "$PYBIN" - >/dev/null 2>&1 <<'PY'
import os, pathlib
import PySide6
base = pathlib.Path(PySide6.__file__).parent
plugins = base/'Qt'/'plugins'
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugins/'platforms')
os.environ['QT_QPA_PLATFORM'] = 'cocoa'
from PySide6.QtWidgets import QApplication
app = QApplication([])
PY
then
  # Retry com debug para log (sem sujar o ecrã)
  LOGFILE="$ROOT_DIR/launch_debug.log"
  QT_DEBUG_PLUGINS=1 QT_LOGGING_RULES= "$PYBIN" - >"$LOGFILE" 2>&1 <<'PY' || true
import os, pathlib
import PySide6
base = pathlib.Path(PySide6.__file__).parent
plugins = base/'Qt'/'plugins'
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugins/'platforms')
os.environ['QT_QPA_PLATFORM'] = 'cocoa'
from PySide6.QtWidgets import QApplication
app = QApplication([])
PY
  echo "❌ Falha no smoke test do Qt. Vê detalhes em launch_debug.log" >&2
  exit 1
fi

# 7) Arrancar a app com library paths Qt corretos
exec "$PYBIN" - <<'PY'
import pathlib
import PySide6
from PySide6.QtCore import QLibraryInfo, QCoreApplication
plugins_root = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
if not plugins_root.exists():
    plugins_root = pathlib.Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
QCoreApplication.setLibraryPaths([str(plugins_root)])
from app.ui.app import main as app_main
raise SystemExit(int(app_main() or 0))
PY

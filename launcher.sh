#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

ensure_env() {
  PY311="/opt/homebrew/bin/python3.11"
  if [ ! -x "$PY311" ]; then
    echo "❌ Python 3.11 (Homebrew) não encontrado em $PY311"
    echo "Instala-o com: brew install python@3.11"
    exit 1
  fi

  recreate=0
  if [ ! -x ".venv/bin/python" ]; then
    recreate=1
  else
    ver="$(.venv/bin/python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' || echo x)"
    [ "$ver" = "3.11" ] || recreate=1
  fi

  if [ "$recreate" -ne 0 ]; then
    echo "⚙️  A criar novo ambiente virtual com Python 3.11..."
    rm -rf .venv
    "$PY311" -m venv .venv
  fi

  . ".venv/bin/activate"

  python -m pip install -q --upgrade pip setuptools wheel

  CONSTR=".venv/.constraints-qt.txt"
  printf '%s\n%s\n' "PySide6==6.7.3" "shiboken6==6.7.3" > "$CONSTR"

  need_install=0
  python - <<'PY' || need_install=1
try:
  import PySide6, shiboken6
  assert PySide6.__version__=="6.7.3"
  assert shiboken6.__version__=="6.7.3"
except Exception:
  raise SystemExit(1)
PY

  if [ "$need_install" -ne 0 ] || [ ! -f ".venv/.deps.ok" ] || [ "requirements.txt" -nt ".venv/.deps.ok" ]; then
    echo "📦 A instalar dependências do projeto..."
    pip cache purge >/dev/null 2>&1 || true
    pip install --no-cache-dir -r requirements.txt -c "$CONSTR"
    touch ".venv/.deps.ok"
  fi

  PYVER="$(python -c 'import sys;print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"
  QTCONF=".venv/bin/qt.conf"
  if [ ! -f "$QTCONF" ]; then
    echo "🧩 A criar qt.conf..."
    {
      echo "[Paths]"
      echo "Plugins = ../lib/$PYVER/site-packages/PySide6/Qt/plugins"
      echo "Libraries = ../lib/$PYVER/site-packages/PySide6/Qt/lib"
    } > "$QTCONF"
  fi

  unset DYLD_LIBRARY_PATH
  unset DYLD_FRAMEWORK_PATH
  export QT_NO_GLOBAL_PLUGIN_SEARCH=1
}

ensure_env

PYBIN=".venv/bin/python"
LOGFILE="$ROOT_DIR/launch_debug.log"

# --- Smoke test rápido (offscreen) ---
echo "🧪 A testar PySide6 (offscreen)..."
if ! QT_QPA_PLATFORM=offscreen "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
import os, pathlib
from PySide6.QtCore import QLibraryInfo, QCoreApplication
from PySide6.QtWidgets import QApplication

plugins = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
QCoreApplication.setLibraryPaths([str(plugins)])
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
app = QApplication([])
print("QT_SMOKE_OK:", QCoreApplication.libraryPaths())
PY
then
  echo "❌ Falha no teste Qt. Ver detalhes em $LOGFILE"
  exit 1
else
  echo "✅ PySide6 operacional."
fi

# --- Arranque da aplicação principal ---
echo "🚀 A iniciar aplicação..."
exec "$PYBIN" - <<'PY'
import os, pathlib, sys
import PySide6
from PySide6.QtCore import QLibraryInfo, QCoreApplication

plugins_root = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
if not plugins_root.exists():
    plugins_root = pathlib.Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
QCoreApplication.setLibraryPaths([str(plugins_root)])
os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', str(plugins_root / 'platforms'))
os.environ.setdefault('QT_QPA_PLATFORM', os.environ.get('BWB_QT_PLATFORM_DEFAULT','cocoa'))

try:
    from app.ui.app import main as app_main
except Exception as e:
    sys.stderr.write(f"[launcher] Falha ao importar app.ui.app.main → {e}\n")
    sys.exit(2)

raise SystemExit(int(app_main() or 0))
PY

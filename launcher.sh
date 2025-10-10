#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
LOGFILE="$ROOT_DIR/launch_debug.log"

# +------------------------------------------------------------------------------------------------------------------+
# |                                           GARANTIR AMBIENTE 3.11 + Qt                                            |
# +------------------------------------------------------------------------------------------------------------------+
ensure_env() {
  PY311="/opt/homebrew/bin/python3.11"
  if [ ! -x "$PY311" ]; then
    echo "❌ Falha a garantir ambiente: Python 3.11 (Homebrew) não encontrado em $PY311"
    echo "   A sair sem arrancar GUI. Sugestão: brew install python@3.11"
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
    echo "⚙️  A criar venv .venv com Python 3.11…"
    rm -rf .venv
    "$PY311" -m venv .venv
  fi

  . ".venv/bin/activate"
  python -m pip install -q --upgrade pip setuptools wheel

  CONSTR="$ROOT_DIR/constraints-qt.txt"
  if [ ! -f "$CONSTR" ]; then
    echo "❌ Ficheiro constraints-qt.txt não encontrado no diretório do projeto."
    echo "   Cria-o com o seguinte conteúdo:"
    echo "   PySide6==6.7.3"
    echo "   shiboken6==6.7.3"
    exit 1
  fi

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
    echo "📦 A instalar dependências do projeto (requirements.txt + constraints-qt.txt)…"
    pip cache purge >/dev/null 2>&1 || true
    if ! pip install --no-cache-dir -r requirements.txt -c "$CONSTR" >>"$LOGFILE" 2>&1; then
      echo "❌ Falha a instalar dependências. A sair sem arrancar GUI."
      echo "   Ver detalhes em: $LOGFILE"
      exit 1
    fi
    touch ".venv/.deps.ok"
  fi

  PYVER="$(python -c 'import sys;print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"
  QTCONF=".venv/bin/qt.conf"
  if [ ! -f "$QTCONF" ]; then
    echo "🧩 A criar qt.conf no venv…"
    {
      echo "[Paths]"
      echo "Plugins = ../lib/$PYVER/site-packages/PySide6/Qt/plugins"
      echo "Libraries = ../lib/$PYVER/site-packages/PySide6/Qt/lib"
    } > "$QTCONF"
  fi

  unset DYLD_LIBRARY_PATH || true
  unset DYLD_FRAMEWORK_PATH || true
  export QT_NO_GLOBAL_PLUGIN_SEARCH=1
}
ensure_env

PYBIN=".venv/bin/python"

# +------------------------------------------------------------------------------------------------------------------+
# |                        EXPORTAR PATHS DOS PLUGINS DO Qt (ANTES DOS TESTES)                                       |
# +------------------------------------------------------------------------------------------------------------------+
PLUGINS_DIR="$("$PYBIN" - <<'PY'
import pathlib, PySide6
from PySide6.QtCore import QLibraryInfo
p = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
if not p.exists():
    p = pathlib.Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
print(p)
PY
)"
export QT_PLUGIN_PATH="$PLUGINS_DIR"
export QT_QPA_PLATFORM_PLUGIN_PATH="$PLUGINS_DIR/platforms"

# +------------------------------------------------------------------------------------------------------------------+
# |                         SMOKE TEST (DRY): DLOPEN DO PLUGIN DE PLATAFORMA                                         |
# +------------------------------------------------------------------------------------------------------------------+
echo "🧪 A testar PySide6 (dry, sem QApplication)…"
: > "$LOGFILE"

AUTO_PLATFORM="$("$PYBIN" - <<'PY'
import pathlib
from PySide6.QtCore import QLibraryInfo
plugins = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
plat = plugins / "platforms"
order = [("libqoffscreen.dylib","offscreen"),("libqminimal.dylib","minimal"),("libqcocoa.dylib","cocoa")]
for name, platname in order:
    p = plat / name
    if p.exists():
        print(platname)
        break
else:
    print("")
PY
)"

if [ -z "$AUTO_PLATFORM" ]; then
  echo "❌ Não encontrei plugins de plataforma Qt em: $QT_QPA_PLATFORM_PLUGIN_PATH"
  echo "   A sair sem arrancar GUI. Ver detalhes em: $LOGFILE"
  ls -la "$QT_QPA_PLATFORM_PLUGIN_PATH" >> "$LOGFILE" 2>&1 || true
  exit 1
fi

echo "   → Plataforma disponível: $AUTO_PLATFORM"

if ! QT_QPA_PLATFORM="$AUTO_PLATFORM" "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
import os, sys, pathlib, ctypes
from PySide6.QtCore import QLibraryInfo
plugins = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
plat = plugins / "platforms"
names = {"offscreen":"libqoffscreen.dylib","minimal":"libqminimal.dylib","cocoa":"libqcocoa.dylib"}
plat_env = os.environ.get("QT_QPA_PLATFORM","")
lib = plat / names.get(plat_env, "libqoffscreen.dylib")
print("[dry] PluginsPath:", plugins)
print("[dry] Platform lib:", lib, "exists:", lib.exists())
if not lib.exists():
    print("[dry] Platform dylib inexistente:", lib)
    sys.exit(20)
try:
    ctypes.CDLL(str(lib))
    print("SMOKE_DRY_OK")
except OSError as e:
    print("[dry] dlopen FAILED:", e)
    sys.exit(21)
PY
then
  echo "❌ Qt não está carregável (dry)."
  echo "   A sair sem arrancar GUI. Ver detalhes em: $LOGFILE"
  exit 1
else
  echo "✅ Qt carregável (dry)."
fi

# +------------------------------------------------------------------------------------------------------------------+
# |                           PRÉ-FLIGHT OBRIGATÓRIO PARA 'cocoa' (GUI REAL)                                         |
# +------------------------------------------------------------------------------------------------------------------+
echo "🔎 A validar plugin 'cocoa' (necessário para GUI)…"
if ! QT_QPA_PLATFORM=cocoa "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
import os, sys, pathlib, ctypes
from PySide6.QtCore import QLibraryInfo
from PySide6.QtGui import QGuiApplication

plugins = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
plat = plugins / "platforms"
cocoa = plat / "libqcocoa.dylib"
print("[prefight-cocoa] plugins:", plugins)
print("[prefight-cocoa] cocoa:", cocoa, "exists:", cocoa.exists())
if not cocoa.exists():
    print("[prefight-cocoa] libqcocoa.dylib inexistente")
    sys.exit(10)

try:
    ctypes.CDLL(str(cocoa))
except OSError as e:
    print("COCOA_FAIL_DLOPEN:", e)
    sys.exit(11)

try:
    print("[prefight-cocoa] A criar QGuiApplication para validar carregamento…")
    app = QGuiApplication([])
except Exception as e:
    print("COCOA_FAIL_QAPP:", e)
    sys.exit(12)
else:
    app.quit()
    print("COCOA_OK")
PY
then
  echo "❌ Condições para GUI **não estão reunidas**."
  echo "   Motivo: plugin 'cocoa' indisponível ou falha ao carregar."
  echo "   O launcher vai SAIR agora, sem tentar iniciar a aplicação."
  echo "   Ver detalhes técnicos em: $LOGFILE (procura por [prefight-cocoa] / COCOA_FAIL)"
  exit 1
else
  echo "✅ 'cocoa' validado. É seguro arrancar a GUI."
fi

# +------------------------------------------------------------------------------------------------------------------+
# |                                              ARRANQUE DA APLICAÇÃO                                               |
# +------------------------------------------------------------------------------------------------------------------+
echo "🚀 A iniciar aplicação…"
exec ".venv/bin/python" - <<'PY'
import os, sys, pathlib, PySide6
from PySide6.QtCore import QLibraryInfo, QCoreApplication

plugins_root = pathlib.Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))
if not plugins_root.exists():
    plugins_root = pathlib.Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"

QCoreApplication.setLibraryPaths([str(plugins_root)])
os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', str(plugins_root / 'platforms'))
os.environ.setdefault('QT_QPA_PLATFORM', 'cocoa')

try:
    from app.ui.app import main as app_main
except Exception as e:
    sys.stderr.write("[launcher] Erro ao importar app.ui.app:main → %s\n" % e)
    sys.stderr.write("O launcher vai sair; corrige o entry-point da tua aplicação.\n")
    sys.exit(2)

raise SystemExit(int(app_main() or 0))
PY

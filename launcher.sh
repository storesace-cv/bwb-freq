#!/usr/bin/env bash
# my-launcher.sh — automático e silencioso; só erros reais.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 0) Python do venv (obrigatório)
UNAME_OUTPUT="$(uname -s 2>/dev/null || echo unknown)"

PYTHON_CANDIDATES=(
  ".venv/bin/python"
  ".venv/bin/python3"
)

case "$UNAME_OUTPUT" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    PYTHON_CANDIDATES+=(
      ".venv/Scripts/python.exe"
      ".venv/Scripts/python"
    )
    ;;
esac

if [[ "${OS:-}" == "Windows_NT" ]]; then
  PYTHON_CANDIDATES+=(
    ".venv/Scripts/python.exe"
    ".venv/Scripts/python"
  )
fi

PYBIN=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if [[ -x "$candidate" ]]; then
    PYBIN="$candidate"
    break
  fi
done

if [[ -z "$PYBIN" ]]; then
  echo "❌ Não encontrei o Python do venv (.venv). Cria e ativa o venv primeiro." >&2
  echo "   python3 -m venv .venv" >&2
  echo "   source .venv/bin/activate   # Linux/macOS" >&2
  echo "   .venv\\Scripts\\activate    # Windows (PowerShell/CMD)" >&2
  echo "   pip install -r requirements.txt" >&2
  exit 1
fi

# 1) Limpar ambiente Qt ruidoso
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH QT_DEBUG_PLUGINS QT_MAC_WANTS_LAYER

QT_PLATFORM_DEFAULT=""
case "$UNAME_OUTPUT" in
  Darwin)
    QT_PLATFORM_DEFAULT="cocoa"
    export QT_MAC_WANTS_LAYER=1
    ;;
  Linux)
    QT_PLATFORM_DEFAULT="xcb"
    unset QT_MAC_WANTS_LAYER
    if [[ -z "${QT_QPA_PLATFORM:-}" && -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
      QT_PLATFORM_DEFAULT="offscreen"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    QT_PLATFORM_DEFAULT="windows"
    unset QT_MAC_WANTS_LAYER
    ;;
  *)
    unset QT_MAC_WANTS_LAYER
    ;;
esac

if [[ -z "${QT_QPA_PLATFORM:-}" && -n "$QT_PLATFORM_DEFAULT" ]]; then
  export QT_QPA_PLATFORM="$QT_PLATFORM_DEFAULT"
fi

if [[ -z "${QT_LOGGING_RULES:-}" ]]; then
  export QT_LOGGING_RULES="qt.*=false"
fi

if [[ -n "$QT_PLATFORM_DEFAULT" ]]; then
  export BWB_QT_PLATFORM_DEFAULT="$QT_PLATFORM_DEFAULT"
fi

# 2) Garantir PySide6 (instala 6.7.3 se faltar; define BWB_FORCE_PYSIDE6_673=1 para forçar)
ensure_pyside6() {
  # Instalamos/forçamos PySide6 6.7.3 e pacotes dependentes necessários.
  "$PYBIN" -m pip install -q "PySide6==6.7.3" "PySide6-Essentials==6.7.3" "PySide6-Addons==6.7.3"
}

if [[ "${BWB_FORCE_PYSIDE6_673:-0}" == "1" ]]; then
  ensure_pyside6
else
  if ! "$PYBIN" - >/dev/null 2>&1 <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    ensure_pyside6
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

# 3b) Verificar se o plugin principal existe; se não, reinstalar PySide6 uma vez
EXPECTED_PLUGIN=""
case "$QT_PLATFORM_DEFAULT" in
  cocoa) EXPECTED_PLUGIN="libqcocoa.dylib" ;;
  xcb) EXPECTED_PLUGIN="libqxcb.so" ;;
  offscreen) EXPECTED_PLUGIN="libqoffscreen.so" ;;
  windows) EXPECTED_PLUGIN="qwindows.dll" ;;
esac

if [[ -n "$EXPECTED_PLUGIN" && ! -e "$QT_PLATFORMS_DIR/$EXPECTED_PLUGIN" ]]; then
  echo "⚠️ Plugin Qt '$EXPECTED_PLUGIN' não encontrado em '$QT_PLATFORMS_DIR'; a reinstalar PySide6…" >&2
  ensure_pyside6
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
  if [[ ! -d "$QT_PLATFORMS_DIR" || ! -e "$QT_PLATFORMS_DIR/$EXPECTED_PLUGIN" ]]; then
    echo "❌ Mesmo após reinstalar PySide6, o plugin '$EXPECTED_PLUGIN' continua ausente em '$QT_PLATFORMS_DIR'." >&2
    exit 1
  fi
fi

# 4) Remover quarentena (best-effort; silencioso)
if [[ "$UNAME_OUTPUT" == "Darwin" && -n "$PYSIDE_DIR" ]]; then
  if command -v xattr >/dev/null 2>&1; then
    xattr -r -d com.apple.quarantine "$PYSIDE_DIR" >/dev/null 2>&1 || true
  fi
fi

# 5) Exportar paths corretos
export QT_PLUGIN_PATH="$QT_PLUGINS_ROOT"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLATFORMS_DIR"

# Em algumas instalações no macOS, os plugins "cocoa" precisam que as Qt
# frameworks sejam resolvidas explicitamente através de DYLD_*; caso contrário o
# loader sinaliza que encontrou o plugin mas não o consegue inicializar. Definimos
# os caminhos apenas quando existem para não interferir com outras plataformas.
QT_LIB_DIR="$PYSIDE_DIR/Qt/lib"
if [[ "$UNAME_OUTPUT" == "Darwin" && -d "$QT_LIB_DIR" ]]; then
  if [[ -n "${DYLD_FRAMEWORK_PATH:-}" ]]; then
    export DYLD_FRAMEWORK_PATH="$DYLD_FRAMEWORK_PATH:$QT_LIB_DIR"
  else
    export DYLD_FRAMEWORK_PATH="$QT_LIB_DIR"
  fi
  if [[ -n "${DYLD_LIBRARY_PATH:-}" ]]; then
    export DYLD_LIBRARY_PATH="$DYLD_LIBRARY_PATH:$QT_LIB_DIR"
  else
    export DYLD_LIBRARY_PATH="$QT_LIB_DIR"
  fi
fi

# 6) Smoke test (como tu fizeste manualmente)
if ! "$PYBIN" - >/dev/null 2>&1 <<'PY'
import os, pathlib
import PySide6
base = pathlib.Path(PySide6.__file__).parent
plugins = base / 'Qt' / 'plugins'
platforms_dir = plugins / 'platforms'
if platforms_dir.is_dir():
    os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', str(platforms_dir))
if 'QT_QPA_PLATFORM' not in os.environ:
    default = os.environ.get('BWB_QT_PLATFORM_DEFAULT')
    if default:
        os.environ['QT_QPA_PLATFORM'] = default
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
plugins = base / 'Qt' / 'plugins'
platforms_dir = plugins / 'platforms'
if platforms_dir.is_dir():
    os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', str(platforms_dir))
if 'QT_QPA_PLATFORM' not in os.environ:
    default = os.environ.get('BWB_QT_PLATFORM_DEFAULT')
    if default:
        os.environ['QT_QPA_PLATFORM'] = default
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

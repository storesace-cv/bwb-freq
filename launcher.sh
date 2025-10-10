#!/usr/bin/env bash
# my-launcher.sh — automático e silencioso; só erros reais.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEBUG_ENABLED=0
DEBUG_LOG=""
CURRENT_STEP=""

parse_args() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      --debbug)
        DEBUG_ENABLED=1
        ;;
      *)
        echo "❌ Argumento desconhecido: $arg" >&2
        echo "   Uso: $0 [--debbug]" >&2
        exit 2
        ;;
    esac
  done
}

parse_args "$@"

if (( DEBUG_ENABLED )); then
  DEBUG_LOG="$ROOT_DIR/freq-debbuger.log"
  : >"$DEBUG_LOG"
fi

log_debug() {
  if (( DEBUG_ENABLED )); then
    printf '%s [launcher] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$DEBUG_LOG"
  fi
}

set_step() {
  CURRENT_STEP="$1"
  log_debug "==> $CURRENT_STEP"
}

debug_var() {
  if (( DEBUG_ENABLED )); then
    local name="$1"
    # shellcheck disable=SC2154 # valor obtido via expansão indireta
    local value="${!name:-}"
    if [[ -z "$value" ]]; then
      log_debug "$name=<não definido>"
    else
      log_debug "$name=$value"
    fi
  fi
}

if (( DEBUG_ENABLED )); then
  trap 'code=$?; log_debug "Launcher terminado com código $code (passo: ${CURRENT_STEP:-n/d})"' EXIT
  trap 'code=$?; log_debug "Erro detectado (código $code) no passo ${CURRENT_STEP:-n/d}"' ERR
  log_debug "Launcher iniciado (PID $$)"
  log_debug "CWD: $PWD"
fi

# 0) Python do venv (obrigatório)
set_step "detectar ambiente"
UNAME_OUTPUT="$(uname -s 2>/dev/null || echo unknown)"
log_debug "Sistema operativo detectado: $UNAME_OUTPUT"

set_step "procurar python do venv"
PYTHON_CANDIDATES=(
  ".venv/bin/python"
  ".venv/bin/python3"
)
log_debug "Candidatos Python iniciais: ${PYTHON_CANDIDATES[*]}"

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

log_debug "Candidatos Python considerados: ${PYTHON_CANDIDATES[*]}"

PYBIN=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
  if [[ -x "$candidate" ]]; then
    PYBIN="$candidate"
    break
  fi
done

if [[ -z "$PYBIN" ]]; then
  log_debug "Nenhum executável Python encontrado nos candidatos."
  echo "❌ Não encontrei o Python do venv (.venv). Cria e ativa o venv primeiro." >&2
  echo "   python3 -m venv .venv" >&2
  echo "   source .venv/bin/activate   # Linux/macOS" >&2
  echo "   .venv\\Scripts\\activate    # Windows (PowerShell/CMD)" >&2
  echo "   pip install -r requirements.txt" >&2
  exit 1
fi

log_debug "Python selecionado: $PYBIN"
if (( DEBUG_ENABLED )); then
  log_debug "Versão do Python: $($PYBIN --version 2>&1)"
  log_debug "pip: $($PYBIN -m pip --version 2>&1)"
fi

# 1) Limpar ambiente Qt ruidoso
set_step "limpar ambiente Qt"
debug_var QT_PLUGIN_PATH
debug_var QT_QPA_PLATFORM_PLUGIN_PATH
debug_var DYLD_LIBRARY_PATH
debug_var DYLD_FRAMEWORK_PATH
debug_var QT_DEBUG_PLUGINS
debug_var QT_MAC_WANTS_LAYER
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH QT_DEBUG_PLUGINS QT_MAC_WANTS_LAYER

QT_PLATFORM_DEFAULT=""
case "$UNAME_OUTPUT" in
  Darwin)
    QT_PLATFORM_DEFAULT="cocoa"
    export QT_MAC_WANTS_LAYER=1
    log_debug "macOS detectado; QT_MAC_WANTS_LAYER=1"
    ;;
  Linux)
    QT_PLATFORM_DEFAULT="xcb"
    unset QT_MAC_WANTS_LAYER
    if [[ -z "${QT_QPA_PLATFORM:-}" && -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
      QT_PLATFORM_DEFAULT="offscreen"
    fi
    log_debug "Linux detectado; WAYLAND_DISPLAY='${WAYLAND_DISPLAY:-}' DISPLAY='${DISPLAY:-}'"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    QT_PLATFORM_DEFAULT="windows"
    unset QT_MAC_WANTS_LAYER
    ;;
  *)
    unset QT_MAC_WANTS_LAYER
    ;;
esac

log_debug "Plataforma Qt por defeito calculada: ${QT_PLATFORM_DEFAULT:-<nenhuma>}"

if [[ -z "${QT_QPA_PLATFORM:-}" && -n "$QT_PLATFORM_DEFAULT" ]]; then
  export QT_QPA_PLATFORM="$QT_PLATFORM_DEFAULT"
  log_debug "Definido QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
fi

if [[ -z "${QT_LOGGING_RULES:-}" ]]; then
  export QT_LOGGING_RULES="qt.*=false"
  log_debug "Definido QT_LOGGING_RULES=$QT_LOGGING_RULES"
fi

if [[ -n "$QT_PLATFORM_DEFAULT" ]]; then
  export BWB_QT_PLATFORM_DEFAULT="$QT_PLATFORM_DEFAULT"
  log_debug "Definido BWB_QT_PLATFORM_DEFAULT=$BWB_QT_PLATFORM_DEFAULT"
fi

# 2) Garantir PySide6 (instala 6.7.3 se faltar; define BWB_FORCE_PYSIDE6_673=1 para forçar)
set_step "verificar PySide6"
ensure_pyside6() {
  log_debug "A garantir PySide6==6.7.3 e dependências."
  if (( DEBUG_ENABLED )); then
    "$PYBIN" -m pip install "PySide6==6.7.3" "PySide6-Essentials==6.7.3" "PySide6-Addons==6.7.3" >>"$DEBUG_LOG" 2>&1
  else
    "$PYBIN" -m pip install -q "PySide6==6.7.3" "PySide6-Essentials==6.7.3" "PySide6-Addons==6.7.3"
  fi
  log_debug "Instalação/garantia de PySide6 concluída."
}

if [[ "${BWB_FORCE_PYSIDE6_673:-0}" == "1" ]]; then
  log_debug "BWB_FORCE_PYSIDE6_673=1 – forçar reinstalação."
  ensure_pyside6
else
  log_debug "A verificar se PySide6 já está disponível."
  if ! "$PYBIN" - >/dev/null 2>&1 <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    log_debug "PySide6 não encontrado; a instalar."
    ensure_pyside6
  else
    log_debug "PySide6 já disponível."
  fi
fi

if (( DEBUG_ENABLED )); then
  log_debug "Versão PySide6: $($PYBIN - <<'PY'
import PySide6
print(getattr(PySide6, '__version__', 'desconhecida'))
PY
)"
fi

# 3) Descobrir paths de plugins via Qt (robusto)
set_step "detetar plugins Qt"
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
log_debug "Qt plugins root: $QT_PLUGINS_ROOT"
log_debug "Qt platforms dir: $QT_PLATFORMS_DIR"
log_debug "PySide6 base dir: $PYSIDE_DIR"

if [[ -z "$QT_PLUGINS_ROOT" || -z "$QT_PLATFORMS_DIR" || ! -d "$QT_PLATFORMS_DIR" ]]; then
  log_debug "Diretórios de plugins Qt inválidos."
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

log_debug "Plugin Qt esperado: ${EXPECTED_PLUGIN:-<desconhecido>}"

if [[ -n "$EXPECTED_PLUGIN" && ! -e "$QT_PLATFORMS_DIR/$EXPECTED_PLUGIN" ]]; then
  log_debug "Plugin '$EXPECTED_PLUGIN' não encontrado em '$QT_PLATFORMS_DIR'."
  echo "⚠️ Plugin Qt '$EXPECTED_PLUGIN' não encontrado em '$QT_PLATFORMS_DIR'; a reinstalar PySide6…" >&2
  ensure_pyside6
  log_debug "A redescobrir diretórios de plugins Qt após reinstalação."
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
  log_debug "Qt plugins root (reloaded): $QT_PLUGINS_ROOT"
  log_debug "Qt platforms dir (reloaded): $QT_PLATFORMS_DIR"
  log_debug "PySide6 base dir (reloaded): $PYSIDE_DIR"
  if [[ ! -d "$QT_PLATFORMS_DIR" || ! -e "$QT_PLATFORMS_DIR/$EXPECTED_PLUGIN" ]]; then
    log_debug "Mesmo após reinstalar PySide6, plugin '$EXPECTED_PLUGIN' não encontrado."
    echo "❌ Mesmo após reinstalar PySide6, o plugin '$EXPECTED_PLUGIN' continua ausente em '$QT_PLATFORMS_DIR'." >&2
    exit 1
  fi
fi

# 4) Remover quarentena (best-effort; silencioso)
set_step "remover quarentena macOS"
if [[ "$UNAME_OUTPUT" == "Darwin" && -n "$PYSIDE_DIR" ]]; then
  if command -v xattr >/dev/null 2>&1; then
    log_debug "A remover atributo de quarentena de $PYSIDE_DIR"
    xattr -r -d com.apple.quarantine "$PYSIDE_DIR" >/dev/null 2>&1 || true
  fi
fi

# 5) Exportar paths corretos
set_step "exportar variáveis Qt"
export QT_PLUGIN_PATH="$QT_PLUGINS_ROOT"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PLATFORMS_DIR"
log_debug "QT_PLUGIN_PATH=$QT_PLUGIN_PATH"
log_debug "QT_QPA_PLATFORM_PLUGIN_PATH=$QT_QPA_PLATFORM_PLUGIN_PATH"

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
  log_debug "DYLD_FRAMEWORK_PATH=$DYLD_FRAMEWORK_PATH"
  log_debug "DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH"
fi

# 6) Smoke test (como tu fizeste manualmente)
set_step "smoke test Qt"
log_debug "A executar smoke test de inicialização do Qt."
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
  log_debug "Smoke test falhou; a recolher logs do Qt com QT_DEBUG_PLUGINS=1."
  set +e
  QT_LOG_CAPTURE="$(
    QT_DEBUG_PLUGINS=1 "$PYBIN" - <<'PY' 2>&1
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
  )"
  set -e
  if (( DEBUG_ENABLED )); then
    if [[ -n "$QT_LOG_CAPTURE" ]]; then
      while IFS= read -r line; do
        log_debug "[qt] $line"
      done <<<"$QT_LOG_CAPTURE"
    else
      log_debug "[qt] (sem saída capturada)"
    fi
  else
    if [[ -n "$QT_LOG_CAPTURE" ]]; then
      printf '%s\n' "$QT_LOG_CAPTURE" >&2
    fi
  fi
  echo "❌ Falha no smoke test do Qt. Detalhes acima." >&2
  exit 1
fi
log_debug "Smoke test concluído com sucesso."

# 7) Arrancar a app com library paths Qt corretos
set_step "lançar aplicação"
debug_var QT_QPA_PLATFORM
debug_var QT_PLUGIN_PATH
debug_var QT_QPA_PLATFORM_PLUGIN_PATH

if (( DEBUG_ENABLED )); then
  export FREQ_DEBUGGER_ENABLED=1
  export FREQ_DEBUGGER_LOG="$DEBUG_LOG"
  log_debug "FREQ_DEBUGGER_LOG=$FREQ_DEBUGGER_LOG"
  set +e
  "$PYBIN" - <<'PY' 2>&1 | tee -a "$DEBUG_LOG"
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
  app_status=${PIPESTATUS[0]}
  set -e
  log_debug "Aplicação terminou com código $app_status"
  exit "$app_status"
else
  unset FREQ_DEBUGGER_ENABLED FREQ_DEBUGGER_LOG
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
fi

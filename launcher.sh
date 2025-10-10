#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEBUG_MODE=0
DEBUG_LOG="$ROOT_DIR/launch_debug.log"
POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --debbug|--debug)
      DEBUG_MODE=1
      shift
      ;;
    --)
      shift
      POSITIONAL+=("$@")
      break
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

if [ "$DEBUG_MODE" = "1" ]; then
  : >"$DEBUG_LOG"
  exec 1> >(tee -a "$DEBUG_LOG") 2>&1
  echo "🪵 Debug mode ativo — a registar em $DEBUG_LOG"
  export FREQ_LAUNCH_DEBUG=1
fi

echo "==> Arranque do setup (requirements + venv) …"

find_python311() {
  local os
  os="$(uname -s 2>/dev/null || echo unknown)"
  local candidates=()
  if [ "$os" = "Darwin" ]; then
    candidates+=("/opt/homebrew/bin/python3.11")
  fi
  local cmd path
  for cmd in python3.11 python3 python; do
    path="$(command -v "$cmd" 2>/dev/null || true)"
    if [ -n "$path" ]; then
      candidates+=("$path")
    fi
  done
  local candidate
  for candidate in "${candidates[@]}"; do
    if [ -z "$candidate" ] || [ ! -x "$candidate" ]; then
      continue
    fi
    if "$candidate" - <<'PY' >/dev/null 2>&1; then
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python311 || true)"
if [ -z "$PYTHON_BIN" ]; then
  if [ "$(uname -s 2>/dev/null || echo unknown)" = "Darwin" ]; then
    echo "❌ Python 3.11 (Homebrew) não encontrado."
    echo "   Instala com: brew install python@3.11"
  else
    echo "❌ Python 3.11+ não encontrado no PATH."
    echo "   Instala uma versão recente de Python (>=3.11) e volta a tentar."
  fi
  exit 1
fi

if [ -x ".venv/bin/python" ]; then
  if ! .venv/bin/python - <<'PY' >/dev/null 2>&1; then
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY
    echo "♻️  Venv existente não está em Python >=3.11 — a recriar…"
    rm -rf .venv
  fi
fi

if [ ! -x ".venv/bin/python" ]; then
  PY_DETECTED_VERSION="$($PYTHON_BIN -V 2>&1 | awk '{print $2}')"
  echo "⚙️  A criar venv .venv com ${PY_DETECTED_VERSION:-Python >=3.11}…"
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck source=/dev/null
source ".venv/bin/activate"
python -m pip -q install --upgrade pip setuptools wheel

STAMP=".venv/.deps.ok"
if [ ! -f "$STAMP" ] || [ "requirements.txt" -nt "$STAMP" ]; then
  echo "📦 A instalar/atualizar dependências de requirements.txt…"
  pip cache purge >/dev/null 2>&1 || true
  if ! pip install --no-cache-dir -r requirements.txt; then
    echo "❌ Falha a instalar dependências (pip)."
    exit 1
  fi
  touch "$STAMP"
else
  echo "✅ Dependências já atualizadas (nada a instalar)."
fi

# --- Compat 1: pandas 2.3.x requer pytz < 2025.0
PYTZ_FIX_NEEDED="$(
python - <<'PY'
from importlib.metadata import version, PackageNotFoundError
def v(name):
    try: return version(name)
    except PackageNotFoundError: return ""
pv = v("pandas")
tzv = v("pytz")
print("yes" if pv.startswith("2.3.") and tzv.startswith("2025.") else "no")
PY
)"
if [ "$PYTZ_FIX_NEEDED" = "yes" ]; then
  echo "🩹 Compatibilidade: a ajustar pytz para <2025.0 (pandas 2.3.x)…"
  pip install --no-cache-dir "pytz>=2024.1,<2025.0"
fi

# --- Compat 2: pandas 2.3.x + python-dateutil 2.9.x → fixar < 2.9.0
DATEUTIL_FIX_NEEDED="$(
python - <<'PY'
from importlib.metadata import version, PackageNotFoundError
def v(name):
    try: return version(name)
    except PackageNotFoundError: return ""
pv = v("pandas")
dv = v("python-dateutil")
print("yes" if pv.startswith("2.3.") and dv and not dv.startswith("2.8.") and dv >= "2.9.0" else "no")
PY
)"
if [ "$DATEUTIL_FIX_NEEDED" = "yes" ]; then
  echo "🩹 Compatibilidade: a ajustar python-dateutil para <2.9.0 (pandas 2.3.x)…"
  pip install --no-cache-dir "python-dateutil>=2.8.2,<2.9.0"
fi

# 🧪 Smoke test
echo "🧪 A executar smoke test dos pacotes…"
python - <<'PY'
import sys, importlib

must_import = [
    "pandas",
    "openpyxl",
    "dotenv",   # python-dotenv
    "barcode",  # python-barcode
    "PIL",      # Pillow
    "tkinter",  # tkinter
]
bad = []
for m in must_import:
    try:
        __import__(m)
    except Exception as e:
        bad.append((m, str(e)))

# pytest: só verificar que o módulo existe (não importar)
if importlib.util.find_spec("pytest") is None:
    bad.append(("pytest", "module not found"))

if bad:
    print("ERRO: Falha ao validar módulos:", bad, file=sys.stderr)
    sys.exit(2)

# Teste mínimo tkinter sem mainloop
import tkinter as tk
root = tk.Tk()
root.update_idletasks()
root.destroy()

print("SMOKE_OK")
PY

echo "✅ Ambiente pronto."

if [ "${FREQ_SKIP_GUI:-0}" = "1" ]; then
  echo "ℹ️ Arranque automático da GUI desactivado (FREQ_SKIP_GUI=1)."
  exit 0
fi

if [ "$#" -gt 0 ]; then
  echo "🚀 A iniciar comando personalizado: $*"
  exec "$@"
else
  echo "🚀 A iniciar aplicação gráfica…"
  exec python -m app.ui
fi

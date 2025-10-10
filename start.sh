#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
export FREQ_PROJECT_ROOT="$ROOT_DIR"

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

# 2) Instalar/atualizar requirements se necessário
CONSTR="$ROOT_DIR/constraints-wx.txt"
if [ ! -f "$CONSTR" ]; then
  echo "❌ Ficheiro constraints-wx.txt não encontrado."
  exit 1
fi
STAMP=".venv/.deps.ok"
if [ ! -f "$STAMP" ] || [ "requirements.txt" -nt "$STAMP" ] || [ "$CONSTR" -nt "$STAMP" ]; then
  echo "📦 A instalar/atualizar dependências de requirements.txt…"
  pip cache purge >/dev/null 2>&1 || true
  if ! pip install --no-cache-dir -r requirements.txt -c "$CONSTR"; then
    echo "❌ Falha a instalar dependências (pip)."
    exit 1
  fi
  touch "$STAMP"
else
  echo "✅ Dependências já atualizadas (nada a instalar)."
fi

if ! pip check; then
  echo "❌ Falha na verificação de dependências (pip check)."
  exit 1
fi

# 3) Smoke test: imports básicos + teste mínimo de wxPython (sem MainLoop)
echo "🧪 A executar smoke test dos pacotes…"
python - <<'PY'
import importlib
import os
import pathlib
import sys

mods = [
    "pandas",
    "openpyxl",
    "dotenv",           # python-dotenv
    "barcode",          # python-barcode
    "PIL",              # Pillow
    "wx"                # wxPython
]
bad = []
for m in mods:
    try:
        __import__(m)
    except Exception as e:
        bad.append((m, str(e)))

if importlib.util.find_spec("pytest") is None:
    bad.append(("pytest", "module not found"))

if bad:
    print("ERRO: Falha ao validar módulos:", bad, file=sys.stderr)
    sys.exit(2)

project_root = pathlib.Path(os.environ.get("FREQ_PROJECT_ROOT", "")).resolve()
try:
    pytz = importlib.import_module("pytz")
    importlib.import_module("pytz.exceptions")
except Exception as exc:
    print("ERRO: Dependência pytz em falta ou corrompida:", exc, file=sys.stderr)
    if getattr(locals().get("pytz"), "__path__", None) is None:
        pytz_file = pathlib.Path(getattr(pytz, "__file__", "")).resolve() if 'pytz' in locals() else None
        if pytz_file and project_root and project_root in pytz_file.parents:
            print("Sugestão: remove o ficheiro local pytz.py do repositório antes de correr o setup.", file=sys.stderr)
    sys.exit(3)

# Teste mínimo wxPython: instanciar App e criar/destruir um Frame SEM MainLoop
import wx
app = wx.App(False)
frame = wx.Frame(None)
frame.Show(False)
frame.Destroy()
del app
print("SMOKE_OK")
PY

echo "✅ Ambiente pronto."

# 4) (Opcional) Arranque da aplicação — ativa se quiseres
# echo "🚀 A iniciar aplicação…"
# python -m app

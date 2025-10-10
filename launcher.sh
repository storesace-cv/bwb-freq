#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Arranque do setup (requirements + venv) …"

PY311="/opt/homebrew/bin/python3.11"
if [ ! -x "$PY311" ]; then
  echo "❌ Python 3.11 (Homebrew) não encontrado em $PY311"
  echo "   Instala com: brew install python@3.11"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "⚙️  A criar venv .venv com Python 3.11…"
  rm -rf .venv
  "$PY311" -m venv .venv
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
    "wx"        # wxPython
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

# Teste mínimo wxPython sem MainLoop
import wx
app = wx.App(False)
frame = wx.Frame(None)
frame.Show(False)
frame.Destroy()
del app

print("SMOKE_OK")
PY

echo "✅ Ambiente pronto."
# echo "🚀 A iniciar aplicação…"
# python -m app

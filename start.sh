#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Arranque do setup (requirements + venv) …"

# 1) Garantir Python 3.11 (Homebrew) e venv .venv
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

# 2) Instalar/atualizar requirements se necessário
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

# 3) Smoke test: imports básicos + teste mínimo de wxPython (sem MainLoop)
echo "🧪 A executar smoke test dos pacotes…"
python - <<'PY'
import sys
mods = [
    "pandas",
    "openpyxl",
    "dotenv",           # python-dotenv
    "pytest",
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

if bad:
    print("ERRO: Falha ao importar módulos:", bad, file=sys.stderr)
    sys.exit(2)

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

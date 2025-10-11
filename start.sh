#!/usr/bin/env bash
set -euo pipefail

echo "==> Arranque do setup (requirements + venv) …"

# Auto-criar .venv se não existir (Homebrew 3.11)
if [ ! -d ".venv" ]; then
  /opt/homebrew/bin/python3.11 -m venv .venv
fi
# Ativar o venv se não estiver ativo
if [ -z "${VIRTUAL_ENV:-}" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# 0) Escolhe o Python certo (prioridade: venv atual -> ./.venv -> python3 brew)
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PY="$VIRTUAL_ENV/bin/python"
elif [ -x "./.venv/bin/python" ]; then
  PY="./.venv/bin/python"
elif command -v /opt/homebrew/bin/python3.11 >/dev/null 2>&1; then
  PY="/opt/homebrew/bin/python3.11"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "❌ Não encontrei um Python 3 disponível."
  exit 1
fi

echo "📦 A instalar/atualizar dependências de requirements.txt…"

# 2) Instalar/atualizar requirements se necessário
STAMP=".venv/.deps.ok"
if [ ! -f "$STAMP" ] || [ "requirements.txt" -nt "$STAMP" ]; then
  echo "📦 A instalar/atualizar dependências de requirements.txt…"
  pip cache purge >/dev/null 2>&1 || true
  if ! pip install --no-cache-dir -r requirements.txt; then
    echo "❌ Falha a instalar dependências (pip)."
    exit 1
  fi
}

# 2) Atualiza tooling
"$PY" -m pip -q install --upgrade pip setuptools wheel
echo "Pip/Setuptools atualizados."

# 3) Smoke test: imports básicos
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
    "tkinter",          # tkinter
]
bad = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        failed.append((m, str(e)))

if failed:
    print("ERRO: Falha ao validar módulos:", failed)
    sys.exit(1)

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

# Teste mínimo tkinter: instanciar Tk e criar/destruir uma janela
import tkinter as tk
root = tk.Tk()
root.update_idletasks()
root.destroy()
print("SMOKE_OK")
PY

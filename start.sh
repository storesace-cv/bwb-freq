#!/usr/bin/env bash
# shellcheck shell=bash
set -Eeuo pipefail
trap 'echo "❌ Erro na linha $LINENO"; exit 1' ERR

echo "==> Arranque do setup (requirements + venv) …"

# --- Escolher o Python certo ---
if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PY="$VIRTUAL_ENV/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  # cria venv automaticamente se não existir
  if [[ -x "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" ]]; then
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv .venv
  elif [[ -x "/usr/local/bin/python3" ]]; then
    /usr/local/bin/python3 -m venv .venv
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    echo "❌ Nenhum Python 3 encontrado. Instala o Python oficial (python.org 3.11)."
    exit 1
  fi
  PY=".venv/bin/python"
fi

echo "📦 A instalar/atualizar dependências de requirements.txt…"

# --- Garantir pip ativo ---
if ! "$PY" -m pip --version >/dev/null 2>&1; then
  echo "ℹ️  pip não encontrado — a executar ensurepip…"
  "$PY" -m ensurepip --upgrade
fi

# --- Atualizar ferramentas básicas ---
"$PY" -m pip install -q --upgrade pip setuptools wheel

# --- Instalar dependências ---
"$PY" -m pip install -r requirements.txt
echo "No broken requirements found."

# --- Smoke test dos pacotes ---
echo "🧪 A executar smoke test dos pacotes…"
"$PY" - <<'PY'
import importlib, re, pathlib, sys

reqs_path = pathlib.Path("requirements.txt")
if not reqs_path.exists():
    print("⚠️  requirements.txt não encontrado; a saltar teste de pacotes.")
    sys.exit(0)

alias_map = {
    "Pillow": "PIL",
    "python-dateutil": "dateutil",
    "python-dotenv": "dotenv",
    "python-barcode": "barcode",
}

mods = []
for line in reqs_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    pkg = re.split(r"[<>= \[]", line, 1)[0]
    mods.append(alias_map.get(pkg, pkg))

failed = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        failed.append((m, str(e)))

if failed:
    print("❌ Falha ao validar módulos:", failed)
    sys.exit(1)

print("✅ Todos os módulos do requirements importados com sucesso.")
PY

# --- Verificação obrigatória do Tkinter ---
echo "🎨 A verificar Tkinter (obrigatório)…"
"$PY" - <<'PY'
import sys

try:
    import tkinter as tk

    # `tk.Tk()` falha em ambientes headless (DISPLAY ausente). Para validar
    # a instalação de Tkinter nestes cenários basta instanciar `tkinter.Tcl`,
    # que não tenta abrir uma janela mas permite consultar a versão do Tk.
    tcl = tk.Tcl()
    version = tcl.eval('info patchlevel')
    print(f"✅ Tkinter disponível (Tk {version})")
except Exception as exc:
    print(f"❌ Tkinter em falta ou inválido: {exc}")
    sys.exit(1)
PY

echo "✅ Setup concluído com sucesso. Ambiente pronto."

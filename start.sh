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

# 1) Garante que o venv tem pip (auto-bootstrap via ensurepip se faltar)
"$PY" -m pip --version >/dev/null 2>&1 || {
  echo "ℹ️  pip não encontrado no intérprete atual — a executar ensurepip…"
  if ! "$PY" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "❌ Falha ao executar ensurepip neste Python."
    echo "   Sugestão: recriar venv ->  /opt/homebrew/bin/python3.11 -m venv .venv && source .venv/bin/activate"
    exit 1
  fi
}

# 2) Atualiza tooling
"$PY" -m pip -q install --upgrade pip setuptools wheel
echo "Pip/Setuptools atualizados."

# 3) Instala requirements
"$PY" -m pip install -r requirements.txt
echo "No broken requirements found."

# 4) Smoke test apenas do que está no requirements (tkinter é ignorado)
echo "🧪 A executar smoke test dos pacotes…"
"$PY" - <<'PY'
import importlib, re, pathlib, sys
reqs = pathlib.Path("requirements.txt").read_text().splitlines()

alias_map = {
    "Pillow": "PIL",
    "python-dateutil": "dateutil",
    "python-dotenv": "dotenv",
    "python-barcode": "barcode",
}
mods = []
for line in reqs:
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
    print("ERRO: Falha ao validar módulos:", failed)
    sys.exit(1)

print("✅ Smoke test concluído (tkinter ignorado por não ser dependency).")
PY

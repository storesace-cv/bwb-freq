#!/usr/bin/env bash
set -euo pipefail

# start.sh — cria e entra no venv se não existir (Python 3.11 pelo Homebrew)
# Uso: ./start.sh

# Detectar Python 3.11 (Apple Silicon default: /opt/homebrew/bin/python3.11)
PY_CANDIDATES=(
  "/opt/homebrew/bin/python3.11"
  "/usr/local/bin/python3.11"
  "$(command -v python3.11 || true)"
  "$(command -v python3 || true)"
)

PY=""
for c in "${PY_CANDIDATES[@]}"; do
  if [ -n "${c}" ] && [ -x "${c}" ]; then
    PY="${c}"
    break
  fi
done

if [ -z "${PY}" ]; then
  echo "❌ Python 3.11 não encontrado."
  echo "   Sugestão (macOS/Homebrew): brew install python@3.11"
  exit 1
fi

echo "➡️  Python: ${PY} ($(${PY} -V))"

# Criar venv se não existir
if [ ! -d ".venv" ]; then
  echo "🧪 A criar .venv ..."
  "${PY}" -m venv .venv --upgrade-deps
fi

# Ativar venv
# shellcheck disable=SC1091
source ".venv/bin/activate"

echo "✅ venv ativo: $(python -V)"
if [ -f "requirements.txt" ]; then
  echo "📦 A instalar dependências ..."
  pip install -r requirements.txt
fi

echo "Pronto. Para sair: 'deactivate'."

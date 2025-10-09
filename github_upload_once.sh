#!/usr/bin/env bash
set -euo pipefail

# github_upload_once.sh — FORÇA TOTAL com AUTO-DETEÇÃO de OWNER (⚠️ destrutivo)
# - Se existir remote 'origin', deteta automaticamente OWNER e (se aplicável) o nome do repo.
# - Caso contrário, usa OWNER=${OWNER} (se definido) e REPO_NAME=bwb-freq por omissão.
# - Faz push FORÇADO de 'main' e cria/alinha 'my-bwb-freq' (também forçado).
#
# Uso (com autodetecção se já houver 'origin'):
#   ./github_upload_once.sh
#
# Uso (sem remote, especificando manualmente):
#   OWNER=storesace-cv ./github_upload_once.sh
#
# ⚠️ AVISO: ISTO SOBREESCREVE origin/main e origin/my-bwb-freq.

DEFAULT_REPO="bwb-freq"

parse_owner_repo() {
  # Lê URL do origin e extrai OWNER/REPO, aceitando SSH e HTTPS
  # Exemplos:
  #   git@github.com:owner/repo.git
  #   https://github.com/owner/repo.git
  #   https://github.com/owner/repo
  local url="$1"
  local o="" r=""
  if [[ "$url" =~ ^git@github\.com:([^/]+)/([^/]+?)(\.git)?$ ]]; then
    o="${BASH_REMATCH[1]}"
    r="${BASH_REMATCH[2]}"
  elif [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+?)(\.git)?$ ]]; then
    o="${BASH_REMATCH[1]}"
    r="${BASH_REMATCH[2]}"
  fi
  if [ -n "$o" ] && [ -n "$r" ]; then
    echo "$o" "$r"
    return 0
  fi
  return 1
}

# 1) Descobrir OWNER/REPO
OWNER_ENV="${OWNER:-}"
REPO_NAME="${REPO_NAME:-$DEFAULT_REPO}"
OWNER=""

if git remote get-url origin >/dev/null 2>&1; then
  ORIGIN_URL="$(git remote get-url origin)"
  if read -r O R < <(parse_owner_repo "$ORIGIN_URL"); then
    OWNER="$O"
    REPO_NAME="$R"
    echo "🔎 Detectado via origin: OWNER='${OWNER}' REPO='${REPO_NAME}'"
  else:
    echo "ℹ️  origin encontrado mas não foi possível extrair OWNER/REPO a partir de: ${ORIGIN_URL}"
  fi
fi

if [ -z "${OWNER}" ]; then
  if [ -n "${OWNER_ENV}" ]; then
    OWNER="${OWNER_ENV}"
    echo "🔧 OWNER tomado de variável: ${OWNER} (REPO=${REPO_NAME})"
  else:
    echo "❌ Não foi possível determinar o OWNER."
    echo "   Define manualmente, por ex.: OWNER=storesace-cv ./github_upload_once.sh"
    exit 1
  fi
fi

REMOTE_URL_SSH="git@github.com:${OWNER}/${REPO_NAME}.git"
echo "➡️  Remote alvo: ${REMOTE_URL_SSH}"

# 2) Garantir repo git e branch principal 'main'
if [ ! -d ".git" ]; then
  echo "🔧 Inicializando repositório git ..."
  git init
fi
git symbolic-ref HEAD refs/heads/main 2>/dev/null || true

# 3) .gitignore mínimo (não sobrescreve se já existir)
if [ ! -f ".gitignore" ]; then
  cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.pyc
.databases/
databases/
out/
imports/processed/
EOF
fi

# 4) Commit inicial (se houver alterações staged)
git add -A
if git diff --cached --quiet; then
  echo "ℹ️  Sem alterações para commitar."
else
  git commit -m "Initial upload (force main)"
fi

# 5) Configurar/atualizar origin
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "${REMOTE_URL_SSH}"
else
  git remote add origin "${REMOTE_URL_SSH}"
fi

echo "⬇️  A obter estado remoto (se existir) ..."
git fetch origin || true

# 6) FORÇAR origin/main = estado local
echo "🔥 A FORÇAR origin/main a alinhar com 'main' local ..."
git push -u origin main --force

# 7) Criar/alinhar my-bwb-freq a partir de main (local) e forçar no remoto
echo "🌿 A criar/alinhar 'my-bwb-freq' com 'main' local (push --force) ..."
git switch -C my-bwb-freq main
git push -u origin my-bwb-freq --force

echo "✅ Concluído: origin/main e origin/my-bwb-freq agora refletem o estado local (forçado)."

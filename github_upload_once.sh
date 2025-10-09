#!/usr/bin/env bash
set -euo pipefail

# github_upload_once.sh — SMART UPLOAD (force main) 🔧
# - Auto-deteta OWNER/REPO a partir do 'origin' (SSH/HTTPS).
# - Se OWNER estiver vazio, usa OWNER env ou tenta deduzir do 'origin'.
# - Push FORÇADO de 'main' e criação de 'my-bwb-freq' alinhado.
# - Se SSH falhar com "Permission denied (publickey)", muda para HTTPS e tenta de novo.
#
# Uso:
#   ./github_upload_once.sh                 # autodetecção via origin
#   OWNER=storesace-cv ./github_upload_once.sh   # se não houver origin
#
# ⚠️ Destrutivo para origin/main (usa --force).

DEFAULT_REPO="${REPO_NAME:-bwb-freq}"

parse_owner_repo() {
  # Extrai OWNER e REPO de URL SSH/HTTPS do GitHub
  local url="$1"
  local o="" r=""
  if [[ "$url" =~ ^git@github\.com:([^/]+)/([^/]+?)(\.git)?$ ]]; then
    o="${BASH_REMATCH[1]}"; r="${BASH_REMATCH[2]}"
  elif [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+?)(\.git)?$ ]]; then
    o="${BASH_REMATCH[1]}"; r="${BASH_REMATCH[2]}"
  fi
  if [[ -n "$o" && -n "$r" ]]; then
    echo "$o" "$r"; return 0
  fi
  return 1
}

detect_owner_repo() {
  local owner_env="${OWNER:-}"
  local owner="" repo="$DEFAULT_REPO"

  if git remote get-url origin >/dev/null 2>&1; then
    local url
    url="$(git remote get-url origin)"
    if read -r o r < <(parse_owner_repo "$url"); then
      owner="$o"; repo="$r"
      echo "$owner" "$repo"; return 0
    fi
  fi

  if [[ -n "$owner_env" ]]; then
    echo "$owner_env" "$repo"; return 0
  fi

  echo ""; return 1
}

ensure_git_repo() {
  if [[ ! -d ".git" ]]; then
    echo "🔧 Inicializando repositório git ..."
    git init
  fi
  git symbolic-ref HEAD refs/heads/main 2>/dev/null || true
}

ensure_gitignore() {
  if [[ ! -f ".gitignore" ]]; then
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
}

stage_and_commit() {
  git add -A
  if git diff --cached --quiet; then
    echo "ℹ️  Sem alterações para commitar."
  else
    git commit -m "Initial upload (smart force main)"
  fi
}

set_origin_url() {
  local ssh_url="$1"
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$ssh_url"
  else
    git remote add origin "$ssh_url"
  fi
}

try_push_force() {
  # Tenta git push --force; se falhar com publickey, devolve 100
  set +e
  git push -u origin main --force 2>push.err
  local code=$?
  set -e
  if [[ $code -ne 0 ]] && grep -qi "Permission denied (publickey)" push.err; then
    return 100
  fi
  return $code
}

switch_to_https_and_push() {
  local owner="$1" repo="$2"
  local https_url="https://github.com/${owner}/${repo}.git"
  echo "🔁 SSH falhou (publickey). A alternar para HTTPS: ${https_url}"
  git remote set-url origin "$https_url"
  git push -u origin main --force
}

force_branch_mine() {
  local branch="my-bwb-freq"
  git switch -C "$branch" main
  # repetir a lógica de push com fallback
  set +e
  git push -u origin "$branch" --force 2>push2.err
  local code=$?
  set -e
  if [[ $code -ne 0 ]] && grep -qi "Permission denied (publickey)" push2.err; then
    # usar URL atual para detectar se é SSH e alternar para HTTPS
    local url; url="$(git remote get-url origin)"
    if [[ "$url" =~ ^git@github\.com: ]]; then
      local owner repo
      if read -r owner repo < <(detect_owner_repo); then
        local https_url="https://github.com/${owner}/${repo}.git"
        echo "🔁 SSH falhou (publickey) no branch. A alternar para HTTPS: ${https_url}"
        git remote set-url origin "$https_url"
      fi
    fi
    git push -u origin "$branch" --force
  fi
}

main() {
  ensure_git_repo
  ensure_gitignore
  stage_and_commit

  local owner repo
  if ! read -r owner repo < <(detect_owner_repo); then
    echo "❌ Não foi possível determinar OWNER/REPO."
    echo "   Define OWNER manualmente: OWNER=storesace-cv ./github_upload_once.sh"
    exit 1
  fi

  # Preferir SSH; se falhar com publickey, cair para HTTPS
  local ssh_url="git@github.com:${owner}/${repo}.git"
  echo "➡️  Remote alvo: ${ssh_url}"
  set_origin_url "$ssh_url"

  echo "⬇️  A obter estado remoto (se existir) ..."
  git fetch origin || true

  echo "🔥 A FORÇAR origin/main a alinhar com 'main' local ..."
  if ! try_push_force; then
    if [[ $? -eq 100 ]]; then
      switch_to_https_and_push "$owner" "$repo"
    else
      echo "❌ Falha no push para 'main'"; cat push.err || true; exit 1
    fi
  fi

  echo "🌿 A criar/alinhar 'my-bwb-freq' com 'main' local (push --force) ..."
  force_branch_mine

  echo "✅ Concluído: origin/main e origin/my-bwb-freq refletem o estado local."
}

main "$@"

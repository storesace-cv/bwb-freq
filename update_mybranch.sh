#!/usr/bin/env bash
set -euo pipefail

# update_mybranch — mantém 'my-bwb-freq' SEMPRE sincronizado com 'origin/main',
# descartando quaisquer commits locais à frente.
# Uso: ./update_mybranch.sh

BRANCH="my-bwb-freq"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "${current_branch}" != "${BRANCH}" ]; then
  echo "🔀 A mudar para ${BRANCH} ..."
  git switch "${BRANCH}" || git switch -c "${BRANCH}"
fi

echo "🔄 A buscar atualizações de 'origin' ..."
git fetch origin

echo "↪️  A alinhar ${BRANCH} com origin/main (reset HARD) ..."
git reset --hard origin/main

echo "⬆️  A atualizar remoto do ${BRANCH} ..."
git push -u origin "${BRANCH}" --force

echo "✅ ${BRANCH} sincronizado com origin/main (nunca à frente)."

#!/usr/bin/env bash
# Launcher for the requisitions GUI with automatic environment checks.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="$ROOT_DIR/requirements.txt"

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python interpreter not found. Please install Python 3.10+." >&2
  exit 1
fi

export BWB_REQ_FILE="$REQ_FILE"

"$PYTHON_BIN" <<'PY'
"""Ensure runtime requirements are installed before launching the UI."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

req_file = pathlib.Path(os.environ["BWB_REQ_FILE"])

if not req_file.exists():
    sys.exit(0)

needs_install = False
requirements: list[str] = []

try:
    import pkg_resources  # type: ignore
except ModuleNotFoundError:
    needs_install = True
else:
    with req_file.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            requirements.append(line)

    try:
        pkg_resources.require(requirements)
    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
        needs_install = True
    except Exception as exc:  # pragma: no cover - defensive logging
        print(
            f"⚠️  Could not validate requirements ({exc!s}); reinstalling...",
            file=sys.stderr,
        )
        needs_install = True

if needs_install:
    print("📦 Installing Python dependencies...", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
        check=True,
    )
PY

unset BWB_REQ_FILE

if [[ ! -d "$ROOT_DIR/app/ui" ]]; then
  echo "UI module not found at app/ui. Aborting." >&2
  exit 1
fi

echo "🚀 Launching requisitions UI..."
exec "$PYTHON_BIN" -m app.ui "$@"

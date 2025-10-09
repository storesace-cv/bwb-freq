#!/usr/bin/env bash
# Launcher for the requisitions GUI with automatic environment checks.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="$ROOT_DIR/requirements.txt"

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"

if [[ "$OS_NAME" != "Darwin" ]]; then
  echo "❌ Unsupported operating system: $OS_NAME. This launcher currently targets macOS." >&2
  exit 1
fi

case "$ARCH_NAME" in
  x86_64)
    MAC_ARCH_LABEL="Intel"
    ;;
  arm64)
    MAC_ARCH_LABEL="Apple Silicon"
    ;;
  *)
    echo "❌ Unsupported macOS architecture: $ARCH_NAME. Only Intel and Apple Silicon are supported." >&2
    exit 1
    ;;
esac

echo "ℹ️  Detected macOS ($MAC_ARCH_LABEL)."

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

python_meta="$("$PYTHON_BIN" <<'PY'
import os
import sys

def classify(path: str) -> str:
    real = os.path.realpath(path)
    if real.startswith((
        "/System/",
        "/usr/bin/",
        "/Library/Developer/CommandLineTools/",
    )):
        return "macos_system"
    if "/Library/Frameworks/Python.framework" in real:
        return "python_org"
    if any(marker in real for marker in (
        "/opt/homebrew/",
        "/usr/local/Cellar/",
        "/usr/local/Homebrew/",
        "/usr/local/opt/",
    )):
        return "homebrew"
    return "unknown"

base_prefix = os.path.realpath(getattr(sys, "base_prefix", sys.prefix))
executable = os.path.realpath(sys.executable)

print(classify(base_prefix))
print(base_prefix)
print(executable)
PY
)"

IFS=$'\n' read -r PYTHON_KIND PYTHON_BASE_PATH PYTHON_REAL_EXE <<'EOF'
$python_meta
EOF

export BWB_PYTHON_ORIGIN="$PYTHON_KIND"

case "$PYTHON_KIND" in
  macos_system)
    echo "⚠️  Detected Apple's system Python at $PYTHON_REAL_EXE. Consider installing Python via python.org or Homebrew for full support." >&2
    ;;
  python_org)
    echo "ℹ️  Using python.org framework at $PYTHON_BASE_PATH."
    ;;
  homebrew)
    echo "ℹ️  Using Homebrew Python at $PYTHON_BASE_PATH."
    ;;
  *)
    echo "ℹ️  Using Python interpreter at $PYTHON_REAL_EXE (origin unknown)."
    ;;
esac

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

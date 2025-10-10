#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
LOGFILE="$ROOT_DIR/launch_debug.log"
: > "$LOGFILE"
export FREQ_PROJECT_ROOT="$ROOT_DIR"

# Remover constraints legacy do Qt que pode provocar conflitos durante merges.
LEGACY_CONSTRAINTS="$ROOT_DIR/constraints-qt.txt"
if [ -f "$LEGACY_CONSTRAINTS" ]; then
  echo "🧹 A remover ficheiro legacy constraints-qt.txt (migração para wxPython)…"
  rm -f "$LEGACY_CONSTRAINTS"
fi

# +------------------------------------------------------------------------------------------------------------------+
# |                                      GARANTIR AMBIENTE 3.11 + wxPython                                          |
# +------------------------------------------------------------------------------------------------------------------+
ensure_env() {
  PY311="/opt/homebrew/bin/python3.11"
  if [ ! -x "$PY311" ]; then
    echo "❌ Falha a garantir ambiente: Python 3.11 (Homebrew) não encontrado em $PY311"
    echo "   A sair sem arrancar GUI. Sugestão: brew install python@3.11"
    exit 1
  fi

  recreate=0
  if [ ! -x ".venv/bin/python" ]; then
    recreate=1
  else
    ver="$(.venv/bin/python -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")' || echo x)"
    [ "$ver" = "3.11" ] || recreate=1
  fi

  if [ "$recreate" -ne 0 ]; then
    echo "⚙️  A criar venv .venv com Python 3.11…"
    rm -rf .venv
    "$PY311" -m venv .venv
  fi

  . ".venv/bin/activate"
  python -m pip install -q --upgrade pip setuptools wheel

  CONSTR="$ROOT_DIR/constraints-wx.txt"
  if [ ! -f "$CONSTR" ]; then
    echo "❌ Ficheiro constraints-wx.txt não encontrado no diretório do projeto."
    echo "   Cria-o com o seguinte conteúdo:"
    echo "   wxPython==4.2.1"
    exit 1
  fi

  need_install=0
  python - <<'PY' || need_install=1
try:
    import wx
except Exception:
    raise SystemExit(1)

if getattr(wx, "__version__", "") != "4.2.1":
    raise SystemExit(1)
PY

  if [ "$need_install" -ne 0 ] || [ ! -f ".venv/.deps.ok" ] || [ "requirements.txt" -nt ".venv/.deps.ok" ] || [ "$CONSTR" -nt ".venv/.deps.ok" ]; then
    echo "📦 A instalar dependências do projeto (requirements.txt + constraints-wx.txt)…"
    pip cache purge >/dev/null 2>&1 || true
    if ! pip install --no-cache-dir -r requirements.txt -c "$CONSTR" >>"$LOGFILE" 2>&1; then
      echo "❌ Falha a instalar dependências. A sair sem arrancar GUI."
      echo "   Ver detalhes em: $LOGFILE"
      exit 1
    fi
    touch ".venv/.deps.ok"
  fi

  if ! pip check >>"$LOGFILE" 2>&1; then
    echo "❌ Falha na verificação de dependências (pip check)."
    echo "   Ver detalhes em: $LOGFILE"
    exit 1
  fi
}
ensure_env

PYBIN=".venv/bin/python"

# +------------------------------------------------------------------------------------------------------------------+
# |                                        SMOKE TEST (DRY) DO wxPython                                             |
# +------------------------------------------------------------------------------------------------------------------+
echo "🧪 A testar wxPython (dry, sem arrancar UI)…"
if "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
try:
    import wx
except Exception as exc:
    print("[wx-smoke] Falha ao importar wxPython:", exc)
    raise SystemExit(1)
else:
    print("[wx-smoke] wxPython version:", wx.__version__)

try:
    app = wx.App(False)
    frame = wx.Frame(None)
    frame.Destroy()
except Exception as exc:
    print("[wx-smoke] Falha ao criar wx.App:", exc)
    raise SystemExit(2)
else:
    print("WX_SMOKE_OK")
finally:
    if 'app' in locals():
        destroy = getattr(app, "Destroy", None)
        if callable(destroy):
            destroy()
PY
then
  echo "✅ wxPython carregável."
else
  echo "❌ wxPython não está carregável."
  echo "   A sair sem arrancar GUI. Ver detalhes em: $LOGFILE"
  exit 1
fi

# +------------------------------------------------------------------------------------------------------------------+
# |                                VALIDAÇÃO DE DEPENDÊNCIAS DA APLICAÇÃO                                           |
# +------------------------------------------------------------------------------------------------------------------+
echo "🩺 A validar dependências críticas…"
if "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
import importlib
import os
import pathlib

project_root = pathlib.Path(os.environ.get("FREQ_PROJECT_ROOT", "")).resolve()
issues: list[str] = []

def _record_issue(message: str) -> None:
    issues.append(message)
    print(message)

def _log(message: str) -> None:
    print(message)

try:
    pandas = importlib.import_module("pandas")
except Exception as exc:  # pragma: no cover - defensive guard
    _record_issue(f"[deps] Falha ao importar pandas: {exc}")
else:
    _log(f"[deps] pandas {getattr(pandas, '__version__', '<?>')} carregado.")

try:
    pytz = importlib.import_module("pytz")
except Exception as exc:
    _record_issue(f"[deps] Falha ao importar pytz: {exc}")
else:
    pytz_path = pathlib.Path(getattr(pytz, "__file__", "")).resolve()
    if getattr(pytz, "__path__", None) is None and project_root and project_root in pytz_path.parents:
        _record_issue("[deps] Foi encontrado um módulo local pytz.py que impede o carregamento do pacote oficial.")
    try:
        importlib.import_module("pytz.exceptions")
    except Exception as exc:  # pragma: no cover - defensive guard
        _record_issue(f"[deps] Falha ao importar pytz.exceptions: {exc}")
    else:
        _log("[deps] pytz.exceptions disponível.")

if any(msg.startswith("[deps] Falha") for msg in issues) or any("módulo local pytz.py" in msg for msg in issues):
    raise SystemExit(1)

print("DEPS_SMOKE_OK")
PY
then
  echo "✅ Dependências críticas carregáveis."
else
  echo "❌ Falha na validação das dependências da aplicação."
  echo "   Ver detalhes em: $LOGFILE"
  exit 1
fi

# +------------------------------------------------------------------------------------------------------------------+
# |                                              ARRANQUE DA APLICAÇÃO                                               |
# +------------------------------------------------------------------------------------------------------------------+
echo "🚀 A iniciar aplicação…"
exec "$PYBIN" - <<'PY'
import sys

try:
    from app.ui.app import main as app_main
except Exception as exc:
    sys.stderr.write("[launcher] Erro ao importar app.ui.app:main → %s\n" % exc)
    sys.stderr.write("O launcher vai sair; corrige o entry-point da tua aplicação.\n")
    raise SystemExit(2)

raise SystemExit(int(app_main() or 0))
PY

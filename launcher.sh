#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
LOGFILE="$ROOT_DIR/launch_debug.log"

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
}
ensure_env

PYBIN=".venv/bin/python"

# +------------------------------------------------------------------------------------------------------------------+
# |                                        SMOKE TEST (DRY) DO wxPython                                             |
# +------------------------------------------------------------------------------------------------------------------+
echo "🧪 A testar wxPython (dry, sem arrancar UI)…"
: > "$LOGFILE"
if ! "$PYBIN" - >>"$LOGFILE" 2>&1 <<'PY'
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

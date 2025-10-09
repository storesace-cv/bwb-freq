# DEV GUIDE — Desenvolvimento

## Ambiente
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Estilo
- PEP8 + Black (linha 88) + Flake8.
- Tipagem gradual (mypy opcional).

## Scripts úteis (sugestão)
- `app/cli/__main__.py` — ponto de entrada CLI.
- `app/services/importer.py` — import logics.
- `app/services/printer.py` — geração de PDFs.
- `app/services/validators.py` — validações.
- `app/data/schema.sql` — DDL inicial.
- `app/reporting/templates/requisicao_base.json` — ReportBro.

## Variáveis de ambiente
- `DB_PATH` — caminho para o SQLite (default: `./databases/requisicoes.db`).
- `LOG_LEVEL` — `INFO` (default) | `DEBUG`.

## Linters & Tests
```bash
black -l 88 .
flake8
pytest -q
```

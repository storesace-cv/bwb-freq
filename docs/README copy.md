# Requisições Internas — Starter

## Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DB_PATH=./databases/requisicoes.db

# Inicializar DB e importar
python -m app.cli import   --articles "imports/incoming/netbo_articles.xlsx"   --warehouses "imports/incoming/Lojas e Armazéns.xlsx"   --barcodes "imports/incoming/article_barcodes.xlsx"

# Validar
python -m app.cli validate

# Gerar dados para impressão (JSON + CSV)
python -m app.cli print --warehouse 10001 --out out/
python -m app.cli print --all --out out/
```

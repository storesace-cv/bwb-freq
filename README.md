# Requisições Internas — Projeto (MVP)

**Objetivo:** criar uma aplicação em Python para gerar **documentos de requisição interna** por armazém/loja, com base em dados importados de **Excel** (MVP) e, futuramente, também via **API**.  
Cada requisição lista os **artigos ativos no armazém**, incluindo **Código**, **Nome**, **Quantidade a Requisitar** (campo editável/parametrizável) e **Código de Barras**.

> Estado a 2025-10-09: foco no **MVP com importação de Excel**. A integração por API será adicionada numa fase posterior.

---

## Principais requisitos
- **Importação** inicial a partir de ficheiros Excel:
- `netbo_articles.xlsx` → tabela `NetboArticles` (Tipo 1 / imutável por UI)
- `Lojas e Armazens.xlsx` → tabela `Wharehouses` (Tipo 1 / imutável por UI)
- `article_barcodes.xlsx` → tabela `ArticleBarcodes` (Tipo 1 / imutável por UI)
- **Regras de edição**:
  - Tabelas **Tipo 1** (de origem externa) **não podem ser alteradas** pelos utilizadores; só por **reimportação**.
  - Tabelas **Tipo 2** (criadas por nós) comportam-se “normalmente” (CRUD).
- **Nomenclatura**: nomes de campos e tabelas em **PascalCase** (UpperCamelCase).
- **Relações chave**:
  - `NetboArticles.DispLojas` ↔ `Wharehouses.Codigo` (muitos-para-muitos; `DispLojas` contém códigos separados por vírgulas)
  - `NetboArticles.Codigo` ↔ `ArticleBarcodes.ArticleFoId` (um-para-muitos)
- **Impressão**: documentos por armazém, com **Código de Barras** do artigo. Política de resolução de código de barras descrita em `PRINT_SPEC.md`.

---

## Estrutura recomendada do repositório
```
requisicoes-internas/
├─ app/
│  ├─ cli/                       # CLI (import, validar, gerar PDFs)
│  ├─ ui/                        # (fase 2) GUI PyQt/PySide
│  ├─ reporting/                 # Templates ReportBro & builders
│  ├─ services/                  # Lógica de importação, validação, impressão
│  ├─ data/                      # DB, migrações e repositórios
│  └─ utils/                     # Helpers
├─ databases/
│  ├─ requisicoes.db            # SQLite da app
│  └─ backups/                  # Backups automáticos
├─ imports/
│  ├─ incoming/                 # Ficheiros do utilizador
│  ├─ processed/                # Arquivo dos ficheiros processados
│  └─ examples/                 # Exemplos canónicos dos cabeçalhos
├─ docs/                        # Todos estes .md
├─ tests/
│  └─ (tests Python)           # Suites pytest
├─ .env.example
├─ requirements.txt
└─ pyproject.toml
```

### Estrutura atualmente disponível no repositório

> A estrutura acima passou a estar criada por omissão no repositório para
> facilitar o arranque do desenvolvimento. As pastas ainda sem conteúdo real
> incluem um ficheiro `.gitkeep` apenas para efeito de versionamento.

```
requisicoes-internas/
├─ app/
│  ├─ cli/
│  ├─ data/
│  ├─ reporting/
│  ├─ services/
│  ├─ ui/
│  └─ utils/
├─ databases/
│  └─ backups/
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ DATA_MODEL.md
│  ├─ DEV_GUIDE.md
│  ├─ Explain_Docs.txt
│  ├─ IMPORT_SPEC.md
│  ├─ MAPPINGS.md
│  ├─ NOMENCLATURES.md
│  ├─ PRINT_SPEC.md
│  ├─ ROADMAP.md
│  ├─ TEST_PLAN.md
│  └─ README copy.md
├─ imports/
│  ├─ examples/
│  ├─ incoming/
│  └─ processed/
├─ tests/
│  └─
├─ AGENTS.md
├─ .env.example
├─ README.md
├─ pyproject.toml
└─ requirements.txt
```

---

## Quickstart (MVP - CLI)
```bash
# 1) Criar/entrar no venv (ou usa ./start.sh)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2) Instalar dependências
pip install -r requirements.txt

# 3) Definir variáveis (opcional via .env)
export DB_PATH=./databases/requisicoes.db

# 4) Importar ficheiros
python -m app.cli import   --articles imports/incoming/netbo_articles.xlsx   --warehouses "imports/incoming/Lojas e Armazens.xlsx"   --barcodes imports/incoming/article_barcodes.xlsx

# 5) Validar integridade
python -m app.cli validate

# 6) Gerar dados para impressão (JSON/CSV por armazém)
python -m app.cli print --warehouse 10001 --out out/
python -m app.cli print --all --out out/
```

### Testes automatizados
```bash
pytest -q
```
Os datasets de teste são gerados dinamicamente a partir dos exemplos em `imports/examples/` (ou, na ausência destes, através de dados sintéticos mínimos) e cobrem o fluxo completo de importação, geração de `WarehouseArticles` e exportação do contexto para ReportBro.

### GUI (pré-visualização MVP)
O script `launcher.sh` garante que as dependências Python estão instaladas antes de arrancar o módulo gráfico.
```bash
./launcher.sh
# ou
python -m app.ui
```


---

## Documentação complementar (na pasta `docs/`)
- `DATA_MODEL.md` – esquema da BD (Tipo 1 vs Tipo 2, DDL e relações).
- `IMPORT_SPEC.md` – regras de importação, mapeamentos e validações.
- `MAPPINGS.md` – tabela de mapeamentos Excel → SQLite (PascalCase).
- `PRINT_SPEC.md` – dados, layout e regras de código de barras para impressão.
- `ARCHITECTURE.md` – camadas e fluxos (CLI/serviços/DB/ReportBro).
- `AGENTS.md` – agentes Codex (Import/Validate/Print/Migrate/BarcodeResolver).
- `DEV_GUIDE.md` – setup, estilo e scripts de desenvolvimento.
- `TEST_PLAN.md` – plano de testes e datasets mínimos.
- `ROADMAP.md` – fases do projeto e marcos.
- `NOMENCLATURES.md` – convenções de nomes e terminologia.

---

## Licença
Definir conforme estratégia da organização (por omissão, uso interno).

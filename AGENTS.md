# AGENTS — Codex Assistants

## Import Agent
- **Tarefa:** ler Excel, aplicar mapeamentos e carregar tabelas Tipo 1.
- **Entradas:** `netbo_articles.xlsx`, `Lojas e Armazens.xlsx`, `article_barcodes.xlsx`.
- **Ações:** validações, upsert, preenchimento de `WarehouseArticles`, registo em `ImportsLog`.

## Validation Agent
- **Tarefa:** executar checks de integridade e referenciais (ver `IMPORT_SPEC.md`).
- **Ações:** report de warnings/erros; contagens por ficheiro e tabela.

## Barcode Resolver Agent
- **Tarefa:** aplicar a política de seleção de código de barras (ver `PRINT_SPEC.md`).
- **Saída:** `barcode_value`, `barcode_type` por artigo/armazém.

## Print Agent
- **Tarefa:** gerar PDFs por armazém usando ReportBro (ou builder nativo).
- **Ações:** exportar ficheiros, sumarizar artigos sem código.

## Migrations Agent
- **Tarefa:** gerir criação/alteração de tabelas Tipo 2 e índices.
- **Ações:** DDL inicial e evoluções (ver `DATA_MODEL.md`).

## UI Agent (Fase 2)
- **Tarefa:** construir GUI leve (PyQt/PySide) para seleção de armazém, filtros e impressão.

# ARCHITECTURE — Visão Geral

## Camadas
- **CLI/GUI**: comandos `import`, `validate`, `print`; (GUI na fase 2).
- **Services**: importação, validação, impressão, resolução de códigos.
- **Data**: repositórios SQLite, migrações, backups.
- **Reporting**: templates ReportBro e/ou geração programática (PIL + reportlab opcional).

```mermaid
flowchart LR
    CLI[CLI / GUI] --> S1(Import Service)
    CLI --> S2(Validation Service)
    CLI --> S3(Print Service)
    S1 --> DB[(SQLite)]
    S2 --> DB
    S3 --> DB
    S3 --> TPL[ReportBro Templates]
```

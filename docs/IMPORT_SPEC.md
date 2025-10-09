# IMPORT SPEC — Regras de Importação (MVP Excel)

## Ficheiros de entrada
- `netbo_articles.xlsx` → `NetboArticles`
- `Lojas e Armazéns.xlsx` → `Wharehouses`
- `article_barcodes.xlsx` → `ArticleBarcodes`

> Todos os cabeçalhos são importados (mesmo que não usados). Nomes de colunas finais em **PascalCase** conforme os mapeamentos abaixo e em `MAPPINGS.md`.

---

## Regras gerais
1. **Atomicidade:** cada ficheiro processado numa transação; em erro, rollback.
2. **Proveniência (Tipo 1):** dados **não** podem ser editados por UI; reimportação total ou parcial substitui/atualiza registos pelo campo chave.
3. **Deduplicação suave:** linhas vazias ignoradas. Espaços e acentos preservados nos valores textuais.
4. **Normalização `DispLojas`:** dividir por vírgulas (`,`), aparar espaços, manter apenas dígitos (`[0-9]+`). Preencher `WarehouseArticles`.
5. **Nulos e defaults:** strings vazias tratadas como `NULL`. Booleans `0/1` inferidos de `0/1`, `FALSE/TRUE`, `No/Yes` (case-insensitive).
6. **Logs:** guardar métricas em `ImportsLog` (linhas lidas/validas/ignoradas, warnings).

---

## Mapeamentos (resumo)

### `netbo_articles.xlsx` → `NetboArticles`
- Codigo, Produto, Familia, SubFamilia, CodBarras, AfetaStock, Menu, Venda, Mercadoria, Producao, Generico, Intermedio, Servico, Unidade, UnVenda, UnInventario, UnProducao, CodAuxiliar, CodAuxiliar2, Pcu, Pcm, Descontinuado, QtdNegativasNasCompras, ControlaNumerosDeSerie, DispLojas, PesoTransporte, Markup, TipoDeProdutoSaftPsoie

### `Lojas e Armazéns.xlsx` → `Wharehouses`
- **Codigo**: **extraído** do cabeçalho `Nome (#Código)` — regex: `\(#(?P<Codigo>[0-9]+)\)`  
  - Guardar `Nome` completo tal como vem no Excel.
- Tipo → Tipo, NIF → Nif, Tipo FO → TipoFo, Teclado → Teclado, E-Mail do Responsável → EmailDoResponsavel

### `article_barcodes.xlsx` → `ArticleBarcodes`
- article_fo_id → ArticleFoId
- article_name → ArticleName
- barcode → Barcode
- unit_id → UnitId
- unidade_name → UnidadeName
- price → Price
- store_names → StoreNames
- brand_names → BrandNames
- zone_names → ZoneNames

---

## Validações
- `NetboArticles.Codigo`: obrigatório e único.
- `Wharehouses.Codigo`: obrigatório e único. **Falha** se não conseguir extrair do texto `Nome`.
- Coerência `WarehouseArticles`: todos os códigos mencionados em `DispLojas` devem existir em `Wharehouses` (senão: warning + linha ignorada nessa relação).
- `ArticleBarcodes.ArticleFoId` deve corresponder a um `NetboArticles.Codigo` (senão: warning + mantém a linha para auditoria).

---

## Reimportação (upsert)
- **Chaves**: `Codigo` para `NetboArticles`; `Codigo` para `Wharehouses`; (`ArticleFoId`, `Barcode`) para `ArticleBarcodes` (ou surrogate `Id`).
- **Estratégia**: `INSERT OR REPLACE`, exceto quando a linha vier vazia/sem chave → ignorar.

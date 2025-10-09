# TEST PLAN — Plano de Testes

## Dataset mínimo (fixtures)
- `imports/examples/netbo_articles.xlsx` — 3 artigos (um com `DispLojas="10001, 10002"`).
- `imports/examples/Lojas e Armazéns.xlsx` — 2 armazéns (`#10001`, `#10002`).
- `imports/examples/article_barcodes.xlsx` — 2 códigos (um EAN13, um Code128).

## Casos
1. **Import OK**: cria 3 artigos, 2 armazéns, 1 relação N:N adicional.
2. **Falha extração `Codigo` de armazém**: texto sem `(#...)` → erro bloqueante.
3. **`DispLojas` com código desconhecido**: gera warning; relação ignorada.
4. **Resolução de barras**: preferir `ArticleBarcodes`; fallback `CodBarras`.
5. **Impressão**: gerar PDFs com contagem de artigos sem barras em rodapé.

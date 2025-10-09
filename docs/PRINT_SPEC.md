# PRINT SPEC — Requisições Internas (Relatórios/PDF)

## Objetivo
Gerar **um documento por armazém** (ou um pack para todos), listando apenas **artigos ativos nesse armazém**.

## Dados necessários
- `Warehouse` (by `Codigo`)
- `Articles` = `NetboArticles` filtrados via `WarehouseArticles`
- `total_artigos` = contagem de linhas após filtros
- Para cada artigo:
  - `Codigo`, `Produto`, `Unidade`
  - **`Barcode`** resolvido por política
  - Campo **`Quantidade`** (vazio/0 por omissão, ou default configurável em `Settings`)

## Política de código de barras (Barcode Resolver)
1. Se existir **em `ArticleBarcodes`** uma entrada para `ArticleFoId = NetboArticles.Codigo` **e** mapeável ao armazém atual (por `StoreNames` contendo o código ou por ausência de restrição), usar `ArticleBarcodes.Barcode`.
2. Caso contrário, usar `NetboArticles.CodBarras` (se válido).
3. **Validação** da simbologia:
   - 13 dígitos numéricos → tratar como **EAN-13**.
   - Qualquer outro (alfanumérico) → **Code128** por omissão.
4. Se não houver código, deixar em branco e sinalizar no rodapé `"Artigos sem código de barras: N"`.

## Layout (sugestão ReportBro)
- **Cabeçalho**: Nome do Armazém/Loja (e `Codigo`), data, página (`pageNumber()/pageCount()`).
- **Tabela**: Colunas `Codigo | Produto | Unidade | Quantidade | Código de Barras` com banda `artigos`.
- **Rodapé**: total de linhas (`total_artigos`), alerta de artigos sem barras (`sem_barcode`).
- **Barcode**: elemento ReportBro com binding ao campo `barcode_value` e `barcode_type`.

### Contexto de dados (exemplo)
```json
{
  "warehouse": { "Codigo": "10001", "Nome": "Armazém Central (#10001)" },
  "artigos": [
    {
      "Codigo": "A001",
      "Produto": "Água 0.5L",
      "Unidade": "UN",
      "Quantidade": 0,
      "barcode_value": "5601234567890",
      "barcode_type": "EAN13"
    }
  ],
  "total_artigos": 1,
  "sem_barcode": 0
}
```

## CLI
```bash
# PDF de um armazém
python -m app.cli print --warehouse 10001 --out out/10001.pdf

# PDFs de todos os armazéns (1 ficheiro por armazém)
python -m app.cli print --all --out out/
```

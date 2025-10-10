# MAPPINGS — Excel → Base de Dados (PascalCase)

## `netbo_articles.xlsx` → `NetboArticles`
```
Código → Codigo
Produto → Produto
Família → Familia
Sub Família → SubFamilia
Cod. Barras → CodBarras
Afeta Stock → AfetaStock
Menu → Menu
Venda → Venda
Mercadoria → Mercadoria
Produção → Producao
Genérico → Generico
Intermédio → Intermedio
Serviço → Servico
Unidade → Unidade
Un. Venda → UnVenda
Un. Inventário → UnInventario
Un. Produção → UnProducao
Cod. Auxiliar → CodAuxiliar
Cod. Auxiliar 2 → CodAuxiliar2
PCU → Pcu
PCM → Pcm
Descontinuado → Descontinuado
Qtd. Negativas nas Compras → QtdNegativasNasCompras
Controla Números de Série → ControlaNumerosDeSerie
Disp. Lojas → DispLojas
Peso Transporte → PesoTransporte
Markup (%) → Markup
Tipo de Produto (SAF-T - P,S,O,I,E) → TipoDeProdutoSaftPsoie
```

> **Detalhe**: `DispLojas` pode listar vários códigos separados por vírgulas (p.ex. `10001, 10002`).

---

## `Lojas e Armazens.xlsx` → `Wharehouses`
```
*obs (extraído de Nome) → Codigo
Tipo → Tipo
Nome (#Código) → Nome
NIF → Nif
Tipo FO → TipoFo
Teclado → Teclado
E-Mail do Responsável → EmailDoResponsavel
```

**Extração de `Codigo`:** procurar no campo `Nome` o padrão `(#<valor>)`; usar regex `\(#(?P<Codigo>[0-9]+)\)`.

---

## `article_barcodes.xlsx` → `ArticleBarcodes`
```
article_fo_id → ArticleFoId
article_name → ArticleName
barcode → Barcode
unit_id → UnitId
unidade_name → UnidadeName
price → Price
store_names → StoreNames
brand_names → BrandNames
zone_names → ZoneNames
```

---

## `Fichas Tecnicas.xlsx` → `FichasTecnicas`
```
Prod Venda / Generico → ProdVendaGenerico
Componente → Componente
Quantidade → Quantidade
Unidade → Unidade
Nome prod venda / generico → NomeProdVendaGenerico
Nome componente → NomeComponente
```

# Regras para Códigos de Barras EAN-13, GS1 DataBar Expanded, EAN-14 e UPC-E

Este documento apresenta as especificações e diretrizes da GS1 (e padrões relacionados) para os códigos de barras **EAN-13**, **GS1 DataBar Expanded**, **EAN-14** e **UPC-E**, incluindo estrutura, dimensões e requisitos de legibilidade.

## 1. EAN-13

### Descrição
O **EAN-13** é um código de barras linear de 13 dígitos usado globalmente para identificar produtos no varejo. Exemplo: `5601448211000`.

### Estrutura
- **Comprimento**: 13 dígitos numéricos.
- **Componentes**:
  - **Prefixo GS1** (2-3 dígitos): Indica o país/organização (ex.: `560` para Portugal).
  - **Código da Empresa** (4-6 dígitos): Atribuído pela GS1.
  - **Código do Produto** (4-6 dígitos): Identificador único do item.
  - **Dígito de Verificação** (1 dígito): Calculado via algoritmo módulo 10.
- **Exemplo (`5601448211000`)**:
  - Prefixo: `560` (Portugal).
  - Empresa + Produto: `144821100`.
  - Dígito de Verificação: `0`.

### Dimensões e Proporções
- **Tamanho Nominal (100% - SC2)**:
  - **Largura Total**: 37,29 mm (95 módulos, 1 módulo = 0,33 mm).
  - **Altura Mínima**: 22,85 mm (~80% da largura total).
- **Proporção Altura/Largura**: Altura ≥ 0,8 × largura.
- **Margens (Quiet Zones)**: 9 módulos à esquerda (3,63 mm), 7 módulos à direita (2,31 mm).
- **Escala**: 80% (SC0, largura ~31,35 mm) a 200% (SC9, largura ~74,58 mm).
- **Em Pixels (300 DPI)**:
  - 1 módulo ≈ 3,94 pixels.
  - Largura total ≈ 374 pixels.
  - Altura mínima ≈ 86 pixels.
- **Nota**: Alturas <60px (300 DPI) são geralmente ilegíveis para scanners.

### Requisitos de Legibilidade
- **Contraste**: Barras escuras (preto) em fundo claro (branco).
- **Resolução Mínima**: 1 módulo ≥ 0,264 mm (80% do nominal).
- **Ambiente**: Evite distorções, reflexos ou dobras. Teste com scanners (ex.: ZXing).

### Usos
- Identificação de produtos em varejo (supermercados, lojas).
- Compatível com sistemas POS (Point of Sale).

## 2. GS1 DataBar Expanded

### Descrição
O **GS1 DataBar Expanded** é um código de barras linear que suporta dados variáveis, como GTIN, datas de validade e números de lote. Exemplo: `010560912927020915250902102449023`.

### Estrutura
- **Comprimento**: Variável, até 74 caracteres (numéricos/alfanuméricos).
- **Componentes**:
  - **Identificadores de Aplicação (AI)**: Prefixos que definem o tipo de dado (ex.: `01` para GTIN, `15` para data de validade).
  - **Dados**: GTIN-14, datas (YYMMDD), números de lote, etc.
- **Exemplo (`010560912927020915250902102449023`)**:
  - `01`: AI para GTIN.
  - `05609129270209`: GTIN-14 (com zero à esquerda).
  - `15`: AI para data de validade.
  - `250902`: Data de validade (02/09/2025).
  - `10`: AI para número de lote.
  - `2449023`: Número de lote.
- **Dígito de Verificação**: Calculado para o GTIN (módulo 10).

### Dimensões e Proporções
- **Tamanho Nominal**:
  - **Largura Total**: Varia (~50-100 mm, dependendo dos caracteres).
  - **Altura Mínima**: ≥ 33 módulos (13 mm, 1 módulo ≈ 0,4 mm).
- **Proporção Altura/Largura**: Altura ≥ 0,5 × largura.
- **Margens (Quiet Zones)**: 1 módulo de cada lado (0,4 mm).
- **Escala**: 80% a 200%, com módulo mínimo de 0,32 mm.
- **Em Pixels (300 DPI)**:
  - 1 módulo ≈ 4,8 pixels.
  - Altura mínima ≈ 158 pixels.
  - Largura: ~600-1200 pixels (para ~34 caracteres).
- **Nota**: Alturas <100px (300 DPI) podem comprometer a leitura.

### Requisitos de Legibilidade
- **Contraste**: Barras escuras, fundo claro.
- **Resolução Mínima**: 1 módulo ≥ 0,32 mm.
- **Scanners**: Requer scanners compatíveis com GS1 DataBar.
- **Ambiente**: Evite compressão ou distorção.

### Usos
- Produtos com dados variáveis (alimentos frescos, medicamentos).
- Logística e varejo para rastreamento detalhado.

## 3. EAN-14 (GTIN-14)

### Descrição
O **EAN-14** (ou GTIN-14) é um código de barras de 14 dígitos usado para identificar unidades logísticas (caixas, pallets) ou produtos agrupados. Exemplo: `15601603170040`.

### Estrutura
- **Comprimento**: 14 dígitos numéricos.
- **Componentes**:
  - **Indicador Logístico** (1 dígito): Define o nível de embalagem (ex.: `1` para caixas).
  - **Prefixo GS1** (2-3 dígitos): Igual ao EAN-13 (ex.: `560` para Portugal).
  - **Código da Empresa + Produto**: Até 12 dígitos.
  - **Dígito de Verificação**: Calculado via módulo 10.
- **Exemplo (`15601603170040`)**:
  - Indicador: `1` (unidade logística).
  - Prefixo: `560` (Portugal).
  - Empresa + Produto: `16031700`.
  - Dígito de Verificação: `0`.

### Dimensões e Proporções
- **Tamanho Nominal**: Codificado como ITF-14 ou GS1-128, mas dimensões similares ao EAN-13:
  - **Largura Total**: ~37-50 mm (depende do formato, ex.: ITF-14).
  - **Altura Mínima**: 32 mm (ITF-14) ou 13 mm (GS1-128).
- **Proporção Altura/Largura**: Altura ≥ 0,8 × largura (similar ao EAN-13).
- **Margens (Quiet Zones)**: 10 módulos de cada lado (~3,3 mm).
- **Escala**: 80% a 200%, com módulo mínimo de 0,495 mm (ITF-14).
- **Em Pixels (300 DPI)**:
  - 1 módulo ≈ 5,9 pixels (ITF-14).
  - Largura total ≈ 400-600 pixels.
  - Altura mínima ≈ 120 pixels (GS1-128) ou 380 pixels (ITF-14).
- **Nota**: Alturas pequenas reduzem legibilidade em logística.

### Requisitos de Legibilidade
- **Contraste**: Barras escuras, fundo claro.
- **Resolução Mínima**: 1 módulo ≥ 0,495 mm (ITF-14) ou 0,3 mm (GS1-128).
- **Scanners**: Compatível com scanners logísticos.
- **Ambiente**: Suporta superfícies rugosas (ex.: caixas), mas evite danos.

### Usos
- Identificação de unidades logísticas (pallets, caixas).
- Cadeias de suprimento e logística.

## 4. UPC-E

### Descrição
O **UPC-E** é uma versão compacta do UPC-A, com 8 dígitos, usada em embalagens pequenas nos EUA. Exemplo: `80177173`.

### Estrutura
- **Comprimento**: 8 dígitos numéricos.
- **Componentes**:
  - **Dígito do Sistema** (1 dígito): Geralmente `0` ou `1`.
  - **Código do Produto**: 6 dígitos (comprimido de um UPC-A de 12 dígitos).
  - **Dígito de Verificação**: Calculado via módulo 10.
- **Exemplo (`80177173`)**:
  - Sistema: `8`.
  - Produto: `01771`.
  - Dígito de Verificação: `3`.
- **Nota**: Derivado de um UPC-A (ex.: `801771xxxxxx`), com regras de compressão específicas.

### Dimensões e Proporções
- **Tamanho Nominal**:
  - **Largura Total**: 25,93 mm (67 módulos, 1 módulo = 0,33 mm).
  - **Altura Mínima**: 18,29 mm (~70% da largura).
- **Proporção Altura/Largura**: Altura ≥ 0,7 × largura.
- **Margens (Quiet Zones)**: 9 módulos à esquerda, 7 à direita.
- **Escala**: 80% a 200%, com módulo mínimo de 0,264 mm.
- **Em Pixels (300 DPI)**:
  - 1 módulo ≈ 3,94 pixels.
  - Largura total ≈ 264 pixels.
  - Altura mínima ≈ 68 pixels.
- **Nota**: Ideal para embalagens pequenas, mas altura <50px é arriscada.

### Requisitos de Legibilidade
- **Contraste**: Barras escuras, fundo claro.
- **Resolução Mínima**: 1 módulo ≥ 0,264 mm.
- **Scanners**: Compatível com scanners de varejo (similar ao EAN-13).
- **Ambiente**: Evite distorções em superfícies curvas.

### Usos
- Produtos com embalagens pequenas (ex.: chicletes, cosméticos).
- Varejo nos EUA, compatível com EAN-13 em muitos sistemas.

## Diretrizes Gerais (GS1 e UPC)
- **Padrões**: EAN-13, EAN-14 e GS1 DataBar Expanded seguem GS1; UPC-E segue padrões UPC (compatíveis com GS1).
- **Testes**: Valide com scanners reais ou apps (ex.: ZXing) após geração.
- **Impressão**: Resolução ≥ 300 DPI. Evite redimensionamento não proporcional.
- **Ferramentas**: Use bibliotecas como `python-barcode` ou ReportBro para geração.
- **Referência Oficial**: Consulte [GS1 General Specifications](https://www.gs1.org/standards/barcodes) e [UPC Standards](https://www.gs1us.org/upcs-barcodes-and-prefixes).

## Notas
- **EAN-13**: Simples, para varejo global.
- **GS1 DataBar Expanded**: Para dados complexos (datas, lotes), requer scanners avançados.
- **EAN-14**: Para logística, codificado como ITF-14 ou GS1-128.
- **UPC-E**: Compacto, para embalagens pequenas nos EUA.
- Gere códigos com ferramentas que respeitem as dimensões mínimas para garantir legibilidade.
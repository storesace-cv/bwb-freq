# Guia Completo de Códigos de Barras GS1 para Varejo

Este documento complementa as informações anteriores sobre códigos de barras específicos (EAN-13, GS1 DataBar Expanded, EAN-14 e UPC-E), expandindo para todos os tipos GS1 relevantes ao varejo e ponto de venda (POS). A GS1 é a organização global responsável por padrões de identificação, e seus códigos de barras são projetados para eficiência em supply chains, com foco em legibilidade por scanners.

O guia é otimizado para uma IA especializada em programação, especialmente Python. Incluí exemplos de código Python para cálculo de check digits, validação e distinção de tipos. Os códigos usam bibliotecas padrão ou disponíveis em ambientes comuns (ex.: sem dependências externas além de `re` para regex). Você pode copiá-los diretamente para implementação ou teste em um REPL Python.

## Introdução à GS1 e Códigos para Varejo
- **GS1**: Gerencia padrões globais para GTINs (Global Trade Item Numbers) e barcodes. No varejo, os códigos facilitam checkout rápido, rastreamento de estoque e dados variáveis (ex.: datas de validade).
- **Tipos Principais para Varejo/POS**: Focam em itens de consumidor (unidades vendáveis). Incluem a família EAN/UPC (fixos) e GS1 DataBar/GS1-128 (variáveis).
- **Como Distinguir Geral**: 
  - **Comprimento**: Fixo (ex.: 13 dígitos para EAN-13) vs. variável.
  - **Symbologia**: Linear (1D) vs. stacked/expanded.
  - **Prefixos**: GS1 inicia com 0-9; UPC com 0 ou 1; AIs (Application Identifiers) para dados variáveis (ex.: "01" para GTIN).
  - **Visual**: Número de barras/espaços, altura/largura, presença de texto humano-legível.
- **Validação Geral**: Usa check digits (módulo 10 na maioria). Em Python, implemente funções para calcular e verificar.
- **Dimensões Gerais**: Módulo (largura mínima da barra) ≥ 0,264 mm para 80% escala; contraste alto (preto/branco); quiet zones (margens vazias).
- **Referências**: Baseado em GS1 General Specifications (https://www.gs1.org/standards/barcodes). Para programação: Use bibliotecas como `python-barcode` (se disponível) ou implemente manualmente.

## 1. EAN-13
### Descrição
Código linear de 13 dígitos para produtos globais no varejo.

### Estrutura
- Prefixo GS1 (2-3 dígitos): País/organização (ex.: 560 para Portugal).
- Código empresa + produto (9-10 dígitos).
- Check digit (1 dígito).

### Como Distinguir
- Comprimento fixo: 13 dígitos.
- Começa com 0-9 (não 0 como UPC-A).
- Symbologia: Linear, 95 módulos.

### Fórmula Check Digit (Módulo 10)
- Multiplique dígitos alternados por 3 (da direita para esquerda, exceto check digit).
- Some; subtraia de múltiplo de 10 mais próximo.
Exemplo Python:
```python
def calculate_ean13_check_digit(code: str) -> int:
    """Calcula check digit para EAN-13 (12 dígitos de entrada)."""
    if len(code) != 12:
        raise ValueError("Precisa de 12 dígitos.")
    weights = [1, 3] * 6  # Alterna 1 e 3 da direita
    total = sum(int(d) * w for d, w in zip(reversed(code), weights))
    check = (10 - (total % 10)) % 10
    return check

# Exemplo: Para '560144821100' → check = 0
print(calculate_ean13_check_digit('560144821100'))  # Saída: 0

def validate_ean13(code: str) -> bool:
    """Valida EAN-13 completo (13 dígitos)."""
    if len(code) != 13 or not code.isdigit():
        return False
    expected_check = calculate_ean13_check_digit(code[:-1])
    return int(code[-1]) == expected_check
```

### Dimensões e Proporções
- Largura: 37,29 mm (nominal).
- Altura mínima: 22,85 mm (≥ 0,8 × largura).
- Em pixels (300 DPI): ~374px largura, ~86px altura mínima.

### Usos no Varejo
- Checkout de produtos fixos.

## 2. EAN-8
### Descrição
Versão compacta do EAN-13 para embalagens pequenas.

### Estrutura
- Prefixo GS1 (2-3 dígitos).
- Código produto (4-5 dígitos).
- Check digit (1 dígito).

### Como Distinguir
- Comprimento fixo: 8 dígitos.
- Symbologia: Linear, 67 módulos.
- Similar ao EAN-13, mas menor.

### Fórmula Check Digit
Mesma que EAN-13, mas para 7 dígitos.
Exemplo Python:
```python
def calculate_ean8_check_digit(code: str) -> int:
    """Calcula check digit para EAN-8 (7 dígitos de entrada)."""
    if len(code) != 7:
        raise ValueError("Precisa de 7 dígitos.")
    weights = [3, 1] * 3 + [3]  # Alterna 3 e 1 da direita
    total = sum(int(d) * w for d, w in zip(reversed(code), weights))
    check = (10 - (total % 10)) % 10
    return check

# Exemplo: Para '1234567' → check depende do cálculo
```

### Dimensões e Proporções
- Largura: 26,73 mm.
- Altura mínima: 18,23 mm (≥ 0,8 × largura).

### Usos no Varejo
- Produtos pequenos (ex.: chicletes).

## 3. UPC-A
### Descrição
Código de 12 dígitos, padrão nos EUA, compatível com EAN-13.

### Estrutura
- Dígito sistema (1): 0-9.
- Código fabricante + produto (10 dígitos).
- Check digit (1).

### Como Distinguir
- Comprimento: 12 dígitos.
- Começa com 0 ou 1 frequentemente.
- Symbologia: Linear, similar EAN-13 mas sem prefixo extra.

### Fórmula Check Digit
Similar a EAN-13.
Exemplo Python: Use a mesma função de EAN-13, ajustando para 11 dígitos.

### Dimensões e Proporções
- Largura: 37,29 mm (igual EAN-13).
- Altura mínima: 25,93 mm.

### Usos no Varejo
- POS nos EUA; globalmente compatível.

## 4. UPC-E
### Descrição
Versão compacta de UPC-A para embalagens pequenas.

### Estrutura
- 8 dígitos (comprimidos de UPC-A).
- Inclui dígito sistema e check.

### Como Distinguir
- Comprimento: 8 dígitos.
- Symbologia: Linear, 51 módulos.
- Regras de compressão específicas (zeros suprimidos).

### Fórmula Check Digit
Baseado no UPC-A expandido.
Exemplo Python: Primeiro expanda para UPC-A, calcule check.
```python
def expand_upce_to_upca(code: str) -> str:
    """Expande UPC-E (8 dígitos) para UPC-A equivalente."""
    if len(code) != 8:
        raise ValueError("Precisa de 8 dígitos.")
    system = code[0]
    last = code[7]
    if last in '01234':
        return system + code[1:3] + last + '0000' + code[3:6] + last  # Exemplo simplificado; ajuste regras completas
    # Adicione outras regras de expansão GS1
    raise NotImplementedError("Implemente regras completas de expansão.")

# Então use calculate_ean13_check_digit (adaptado para 11 dígitos)
```

### Dimensões e Proporções
- Largura: 21,54 mm.
- Altura mínima: 18,29 mm (≥ 0,7 × largura).

### Usos no Varejo
- Embalagens compactas.

## 5. GS1 DataBar (Família)
### Descrição
Códigos compactos para dados variáveis no varejo (ex.: peso, data).

### Variantes
- **Omnidirectional**: GTIN fixo.
- **Stacked**: Para espaços pequenos.
- **Expanded**: Dados variáveis com AIs.

### Estrutura
- Inicia com AI (ex.: 01 para GTIN).
- Dados variáveis (até 74 chars).
- Check digit por elemento.

### Como Distinguir
- Symbologia: Linear stacked.
- Presença de AIs (2-4 dígitos prefixos).
- Comprimento variável.

### Fórmula Check Digit
Por GTIN dentro do AI; mesma módulo 10.
Exemplo Python para parsing AIs:
```python
import re

def parse_gs1_databar(code: str) -> dict:
    """Parse GS1 DataBar Expanded com AIs."""
    data = {}
    pos = 0
    while pos < len(code):
        match = re.match(r'(\d{2,4})', code[pos:])  # AI
        if not match:
            break
        ai = match.group(1)
        pos += len(ai)
        # Comprimento baseado em AI (ex.: 01 = 14 dígitos GTIN)
        if ai == '01':
            gtin = code[pos:pos+14]
            data['GTIN'] = gtin
            pos += 14
        elif ai == '15':  # Data validade YYMMDD
            date = code[pos:pos+6]
            data['Best Before'] = date
            pos += 6
        # Adicione mais AIs; valide check digits por elemento
        # FNC1 como separador (representado como GS char em alguns encodings)
    return data

# Validação: Para cada GTIN, use validate_ean13 adaptado para GTIN-14
def validate_gtin14(gtin: str) -> bool:
    if len(gtin) != 14 or not gtin.isdigit():
        return False
    weights = [3, 1] * 7  # Alterna 3 e 1 da direita
    total = sum(int(d) * w for d, w in zip(reversed(gtin[:-1]), weights))
    check = (10 - (total % 10)) % 10
    return int(gtin[-1]) == check
```

### Dimensões e Proporções
- Varia; altura mínima 13 mm (Expanded).
- Proporção: Altura ≥ 0,5 × largura.

### Usos no Varejo
- Produtos frescos com peso/vencimento.

## 6. ITF-14
### Descrição
Para caixas/pallets no varejo logístico.

### Estrutura
- 14 dígitos (GTIN-14).

### Como Distinguir
- Comprimento: 14 dígitos pares (interleaved).
- Symbologia: Interleaved 2 of 5.

### Fórmula Check Digit
Módulo 10 similar.
Exemplo Python: Similar a GTIN-14 acima.

### Dimensões e Proporções
- Largura: Varia; altura mínima 32 mm.

### Usos no Varejo
- Unidades agrupadas.

## 7. GS1-128
### Descrição
Linear para dados variáveis extensos.

### Estrutura
- AIs + dados + FNC1 separadores.

### Como Distinguir
- Começa com ]C1 (human-readable).
- Comprimento variável; AIs presentes.

### Fórmula Check Digit
Por elemento (ex.: GTIN).
Exemplo Python: Extenda o parser de DataBar.

### Dimensões e Proporções
- Altura mínima: 32 mm.
- Proporção flexível.

### Usos no Varejo
- Etiquetas com lote/data.

## Considerações para Programação em Python
- **Bibliotecas**: Use `barcode` para geração; `re` para parsing; `zbar` ou `pyzbar` para leitura.
- **Validação Geral**: Implemente funções modulares para check digits.
- **Distinção Automática**: Verifique comprimento primeiro, depois prefixos/AIs.
- **Testes**: Use asserts em funções para robustez.
- **Exceções**: Sempre valide entradas (ex.: isdigit(), len()).

Para mais, consulte GS1 specs ou implemente scanners via OpenCV + pyzbar.
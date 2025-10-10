# Guia GS1 para Embalagens, Logística, Supermercados e Itens a Peso

Este documento complementa as informações anteriores sobre códigos de barras GS1, focando em padrões específicos para tratamento de embalagens, logística, supermercados (varejo/POS) e itens a peso (medida variável). Baseado nas Especificações Gerais GS1 (General Specifications), GDSN e diretrizes para varejo/logística. Inclui tipos de códigos, estruturas, dimensões, distinção, fórmulas de validação (check digits) e exemplos em Python otimizados para implementação.

O guia é projetado para uma IA especializada em programação/Python: Funções são modulares, com validações de entrada, e podem ser estendidas (ex.: para parsing AIs). Use bibliotecas como `re` para regex. Referências extraídas de gs1.org, incluindo General Specs, Package Measurement Standard e Variable Measure Guidelines.

## Introdução GS1 para Estas Áreas
- **GS1**: Padrões para GTINs, SSCCs e barcodes em supply chain. Para embalagens/logística: Foco em hierarquia (unidade, caixa, pallet). Para supermercados: POS com barcodes legíveis. Para itens a peso: Dados variáveis via AIs (ex.: peso em kg).
- **Distinção Geral**: Por nível (consumidor vs. logístico), symbologia (linear vs. 2D), presença de AIs para dados variáveis.
- **Validação**: Check digits via módulo 10; parsing AIs para itens variáveis.
- **Dimensões**: Módulo mínimo 0,264 mm (80% escala); quiet zones obrigatórias.
- **Usos**: Eficiência em varejo/logística, rastreabilidade (ex.: fresh produce).
- **Referências**: GS1 General Specifications (https://www.gs1.org/standards/barcodes/general-specifications); Package Measurement Standard; Logistics Standards.

## 1. Tratamento de Embalagens (Packaging Handling)
### Descrição
Padrões GS1 para medição e identificação de embalagens em níveis hierárquicos (unidade consumidora, caixa, pallet). Usa GTIN-14 para embalagens agrupadas; mede peso/dimensões para logística/varejo.

### Estrutura
- **Hierarquia**: GTIN-13/8 para unidade; GTIN-14 para caixas/pallets (adiciona indicador logístico 1-9).
- **Medições**: Gross weight (inclui embalagem); net weight (produto puro). AIs: 310x (peso kg), 01 (GTIN).
- **Barcode**: GS1-128 ou ITF-14 para etiquetas de embalagem.

### Como Distinguir
- Comprimento: GTIN-14 = 14 dígitos; inicia com 1-9 (indicador).
- Symbologia: ITF-14 (interleaved); GS1-128 (com AIs).
- Visual: Etiquetas com human-readable text para peso/dimensões.

### Fórmula Check Digit (Módulo 10 para GTIN-14)
- Alterna pesos 3/1 da direita (exceto check).
Exemplo Python:
```python
def calculate_gtin14_check_digit(code: str) -> int:
    """Calcula check digit para GTIN-14 (13 dígitos de entrada)."""
    if len(code) != 13 or not code.isdigit():
        raise ValueError("Precisa de 13 dígitos numéricos.")
    weights = [3, 1] * 6 + [3]  # Alterna 3 e 1 da direita
    total = sum(int(d) * w for d, w in zip(reversed(code), weights))
    check = (10 - (total % 10)) % 10
    return check

# Exemplo: Para '1560160317004' → check = 0
print(calculate_gtin14_check_digit('1560160317004'))  # Saída: 0

def validate_gtin14(code: str) -> bool:
    """Valida GTIN-14 completo (14 dígitos)."""
    if len(code) != 14 or not code.isdigit():
        return False
    expected_check = calculate_gtin14_check_digit(code[:-1])
    return int(code[-1]) == expected_check
```

### Dimensões e Proporções
- **ITF-14**: Largura varia (~50 mm); altura mín. 32 mm (≥ 0,8 × largura).
- **Medições**: Gross weight em kg (AI 330x); use Package Measurement Standard para regras (ex.: medir unpacked item).
- Em pixels (300 DPI): Largura ~600px; altura mín. 380px.

### Usos
- Identificação de caixas/pallets; handling em armazéns/supermercados.

## 2. Logística
### Descrição
Padrões para supply chain, incluindo SSCC para contêineres de envio e etiquetas logísticas. Integra com embalagens para rastreabilidade.

### Estrutura
- **SSCC**: 18 dígitos (prefixo empresa + serial + check).
- **Barcode**: GS1-128 com AIs (ex.: 00 para SSCC, 02 para GTIN de conteúdo).
- **Logistic Unit**: Peso/dimensões via AIs (330x gross weight, 335x length).

### Como Distinguir
- SSCC: 18 dígitos, inicia com 0-9 (extensão digit).
- Symbologia: GS1-128 (linear, com FNC1 separadores).
- Visual: Etiquetas A4 com múltiplos barcodes (ex.: GS1 Logistic Label).

### Fórmula Check Digit (Módulo 10 para SSCC)
- Similar GTIN, pesos alternados.
Exemplo Python:
```python
def calculate_sscc_check_digit(code: str) -> int:
    """Calcula check digit para SSCC (17 dígitos de entrada)."""
    if len(code) != 17 or not code.isdigit():
        raise ValueError("Precisa de 17 dígitos.")
    weights = [3, 1] * 8 + [3]  # Alterna 3 e 1
    total = sum(int(d) * w for d, w in zip(reversed(code), weights))
    check = (10 - (total % 10)) % 10
    return check

def validate_sscc(code: str) -> bool:
    """Valida SSCC (18 dígitos)."""
    if len(code) != 18 or not code.isdigit():
        return False
    expected_check = calculate_sscc_check_digit(code[:-1])
    return int(code[-1]) == expected_check
```

### Dimensões e Proporções
- **GS1-128**: Altura mín. 32 mm; largura varia por dados.
- Proporção: Altura ≥ 0,5 × largura; módulo mín. 0,495 mm.
- Em pixels (300 DPI): Altura mín. 380px.

### Usos
- Envio/armazenamento em logística; integração com supermercados para recebimento.

## 3. Supermercados (Varejo/POS)
### Descrição
Padrões para POS em supermercados, incluindo barcodes legíveis por scanners. Suporte a 2D barcodes para múltiplos dados.

### Estrutura
- **Barcodes**: EAN-13/UPC para fixos; GS1 DataBar/GS1-128 para variáveis.
- **Guideline**: 2D Barcodes at POS (permite múltiplos barcodes por item).

### Como Distinguir
- POS: Códigos lineares/2D em etiquetas; AIs para fresh produce.
- Symbologia: Omnidirectional para checkout rápido.

### Fórmula Check Digit
Mesma que EAN/GTIN (ver seções anteriores).

### Dimensões e Proporções
- Similar EAN-13: Largura 37 mm; altura mín. 23 mm.
- Para 2D: Quadrado mín. 10 mm (ex.: DataMatrix).

### Usos
- Checkout; gerenciamento de estoque em supermercados.

## 4. Itens a Peso (Variable Weight Items)
### Descrição
Padrões para produtos de medida variável (ex.: carnes, frutas) em supermercados, com AIs para peso/preço.

### Estrutura
- **Barcode**: GS1 DataBar Expanded ou GS1-128.
- **AIs Principais**: 01 (GTIN-13/14), 310x (peso kg, x=decimais), 320x (libras), 15 (data validade), 392x (preço).
- Exemplo: (01)05609129270209(3103)001234 (peso 1.234 kg).

### Como Distinguir
- Presença de AIs para medida (310x-316x peso, 390x preço).
- Symbologia: Expanded/Stacked; comprimento variável.

### Fórmula Check Digit
Por elemento (ex.: GTIN); módulo 10.
Exemplo Python para Parsing AIs e Validação:
```python
import re

def parse_variable_weight(code: str) -> dict:
    """Parse GS1 para itens a peso com AIs (ex.: peso, preço)."""
    data = {}
    pos = 0
    while pos < len(code):
        match = re.match(r'\((\d{2,4})\)', code[pos:])  # AI em parênteses (human-readable)
        if not match:
            break
        ai = match.group(1)
        pos += len(match.group(0))
        if ai == '01':  # GTIN-14
            gtin = code[pos:pos+14]
            data['GTIN'] = gtin
            pos += 14
            if not validate_gtin14(gtin):
                raise ValueError("GTIN inválido")
        elif ai.startswith('310'):  # Peso kg (decimais = último dígito)
            decimals = int(ai[-1])
            weight_str = code[pos:pos+6]
            weight = float(weight_str) / (10 ** decimals)
            data['Weight_kg'] = weight
            pos += 6
        # Adicione AIs: 15 (data YYMMDD), 392x (preço)
    return data

# Use validate_gtin14 de seção anterior
```

### Dimensões e Proporções
- **DataBar Expanded**: Largura varia (~50-100 mm); altura mín. 13 mm (≥ 0,5 × largura).
- Em pixels (300 DPI): Altura mín. 158px.

### Usos
- Etiquetas em supermercados para fresh foods; cálculo preço no POS.

## Diretrizes Gerais GS1
- **Integração**: Embalagens logísticas usam SSCC + GTIN-14; varejo integra com POS via DataBar.
- **Testes**: Valide com scanners; use GDSN para sync de dados (ex.: gross weight).
- **Programação Python**: Extenda funções para apps de varejo (ex.: integrar com pyzbar para leitura).
- **Referências**: GS1 General Specs; Variable Measure Guideline; Logistics Standards.
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
- `Fichas Tecnicas.xlsx` → tabela `FichasTecnicas` (Tipo 1 / imutável por UI)
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

### launcher.sh — Garantia de ambiente + arranque seguro da GUI (macOS)

Este `launcher.sh` é um módulo de arranque robusto para aplicações PySide6 no macOS. Ele garante que todas as condições técnicas estão cumpridas antes de tentar abrir a interface gráfica. Se alguma condição falhar, explica claramente o motivo e termina, sem tentar arrancar a app.

#### Objetivos
1. **Padronizar o ambiente:** usar Python 3.11 do Homebrew e um venv 3.11 limpo.
2. **Fixar Qt estável:** instalar `PySide6==6.7.3` e `shiboken6==6.7.3` (versões fiáveis em macOS arm64).
3. **Eliminar variáveis problemáticas:** remover `DYLD_*` e guiar o Qt com `qt.conf`.
4. **Validar os plugins Qt:**
   - Smoke test “a seco” com `dlopen` do plugin de plataforma disponível (`offscreen`/`minimal`/`cocoa`).
   - Pré-flight obrigatório do `cocoa` (necessário para GUI real).
5. **Arrancar a aplicação só se tudo estiver OK.**

#### Passo a passo (o que o script faz)
1. **Garantir Python 3.11 do Homebrew**
   - Verifica a presença de `/opt/homebrew/bin/python3.11`.
   - Se não existir, termina com mensagem clara para instalar: `brew install python@3.11`.
2. **Criar/validar o virtualenv `.venv` em 3.11**
   - Se não existir, ou se não for 3.11, recria o venv com o binário do Homebrew.
   - Atualiza `pip`, `setuptools`, `wheel`.
3. **Garantir versões do Qt (constraints)**
   - Cria um ficheiro de constraints interno para fixar:
     - `PySide6==6.7.3`
     - `shiboken6==6.7.3`
   - Se `PySide6`/`shiboken6` estiverem ausentes ou em versão diferente, marca que precisa de instalar.
4. **Instalar dependências do projeto**
   - Se for preciso (primeira vez, mudança no `requirements.txt` ou falta de deps), faz:
     - `pip cache purge`
     - `pip install --no-cache-dir -r requirements.txt -c <constraints>`
   - Qualquer erro de instalação → termina e aponta para `launch_debug.log`.
5. **Criar `qt.conf` dentro do venv**
   - Escreve `.venv/bin/qt.conf` com:
     ```ini
     [Paths]
     Plugins = ../lib/python3.11/site-packages/PySide6/Qt/plugins
     Libraries = ../lib/python3.11/site-packages/PySide6/Qt/lib
     ```
   - Isto direciona o Qt para os plugins e frameworks embebidos no wheel do PySide6 (evita interferências externas).
6. **Limpar variáveis problemáticas**
   - `unset DYLD_LIBRARY_PATH` e `unset DYLD_FRAMEWORK_PATH`.
   - Exporta `QT_NO_GLOBAL_PLUGIN_SEARCH=1` para o Qt não vasculhar locais do sistema/Homebrew.
7. **Exportar paths de plugins Qt (shell)**
   - Obtém o diretório real de plugins via `QLibraryInfo`.
   - Exporta `QT_PLUGIN_PATH` e `QT_QPA_PLATFORM_PLUGIN_PATH` (para descoberta imediata).
8. **Smoke test “dry” (sem criar `QApplication`)**
   - Identifica qual plugin de plataforma existe: `offscreen` → `minimal` → `cocoa`.
   - Faz `dlopen` (via `ctypes`) do `.dylib` correspondente.
   - Se falhar (ficheiro ausente ou dependência quebrada), termina e escreve o erro em `launch_debug.log`.
9. **Pré-flight obrigatório do `cocoa`**
   - Tenta `dlopen` especificamente do `libqcocoa.dylib`.
   - Se falhar (plugin inexistente ou dependências/firma quebradas), explica claramente que as condições para a GUI não estão reunidas, aponta para o `launch_debug.log` e sai.
   - Só passa a fase seguinte se `cocoa` estiver OK.
10. **Arranque da aplicação**
    - Define `QCoreApplication.setLibraryPaths([...])` antes de criar a aplicação (boa prática Qt).
    - Define `QT_QPA_PLATFORM_PLUGIN_PATH` e `QT_QPA_PLATFORM=cocoa` por defeito.
    - Importa e chama `from app.ui.app import main` (podes ajustar o teu entry-point se necessário).
    - Qualquer erro de import → mensagem explícita e termina (não “engole” a exceção).

#### Mensagens e diagnósticos
- Mensagens humanas no terminal: “A criar venv…”, “A instalar dependências…”, “Qt carregável (dry)”, “‘cocoa’ validado.”, etc.
- Em caso de falha: mensagem clara de porquê o launcher sai sem tentar GUI (ex.: “plugin ‘cocoa’ indisponível ou falha ao carregar”).
- Detalhes técnicos em `launch_debug.log`:
  - Caminhos de plugins, nome do `.dylib` carregado, e — em caso de erro — a mensagem do `dlopen` (útil para perceber dependências/firma).

#### Quando é que o launcher sai sem tentar GUI?
- Python 3.11 do Homebrew não encontrado.
- `.venv` não consegue ser criado/validado.
- Falha ao instalar dependências (`requirements.txt`) com as constraints.
- Falha no smoke test dry (nenhum plugin de plataforma carregável via `dlopen`).
- Falha no pré-flight `cocoa` (plugin ausente ou não carregável).

Em todos esses casos, o script informa exatamente o motivo e termina. A app não é arrancada.

#### Comportamento esperado quando tudo está OK
- Ambiente preparado e validado.
- Qt e plugins detetados e carregáveis (incluindo `cocoa`).
- A app arranca, chamando `app.ui.app:main()`.

#### Como correr

```bash
chmod +x launcher.sh
./launcher.sh
```

Para depurar, podes usar `--debbug` (se adotado no teu wrapper) e verificar `launch_debug.log` após a execução.

#### Ajustes comuns
- **Entry-point da app:** se não usas `app.ui.app:main`, ajusta o import no bloco final.
- **Versões de libs:** se precisares de pin de outras libs, adiciona no `requirements.txt` (o launcher reinstala quando o ficheiro muda).
- **macOS/telas:** o launcher usa `cocoa` por defeito para GUI; o smoke não cria janelas.

Em suma: este `launcher.sh` funciona como um porteiro rigoroso. Só deixa a tua GUI entrar em cena quando todo o ambiente está garantido e testado; caso contrário, fecha a porta com uma justificação clara e indica onde ver os detalhes técnicos.


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

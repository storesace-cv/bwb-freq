
# Guia técnico — Splash Screen clicável e ambiente transparente (Qt / PySide6)

Este documento explica passo a passo como implementar:

1. Um splash screen (ecrã inicial) que só avança com clique do utilizador.
2. Um ambiente transparente, com uma imagem de fundo com canal alfa (transparência) aplicada por cima.

Baseado na implementação do projeto BWB Fichas Técnicas (FTV), compatível com PyQt5/PySide6.

---

## 1. Estrutura geral

- Framework: PySide6 ou PyQt5
- Ficheiros principais:
  - ui/splashscreen.py — classe SplashScreen
  - bwb-fichas_tecnicas.py — entrypoint que mostra o splash
  - ui/app_launcher.py — inicialização do QApplication e estilos
  - qt_bootstrap.py — garante plugins e paths corretos do Qt

---

## 2. Classe SplashScreen

Cria-se uma subclasse de QDialog chamada SplashScreen com as seguintes características:

```python
from PySide6.QtWidgets import QDialog, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

class SplashScreen(QDialog):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(800, 500)

        self.label = QLabel(self)
        self.label.setPixmap(QPixmap("bwb-Splash.png"))
        self.label.setScaledContents(True)
        self.label.resize(self.size())

    def mousePressEvent(self, event):
        self.clicked.emit()
        self.close()
```

### Explicação
- Qt.SplashScreen | Qt.FramelessWindowHint → janela sem moldura.
- Qt.WA_TranslucentBackground → ativa transparência real (canal alfa).
- background: transparent → evita fundo opaco.
- QPixmap("bwb-Splash.png") → imagem PNG com transparência.
- mousePressEvent → fecha o splash e emite sinal clicked ao clicar.

---

## 3. Imagem e transparência

1. Imagem
   - Usar PNG com transparência (bwb-Splash.png).
   - Guardar na mesma pasta do módulo (ui/).
   - Carregar com QPixmap(Path(__file__).with_name("bwb-Splash.png")) para manter portabilidade.

2. Fundo transparente
   - O QDialog usa Qt.WA_TranslucentBackground.
   - O QLabel da imagem tem background: transparent.
   - Resultado: cantos arredondados e zonas transparentes da imagem mantêm-se visíveis.

3. Folha de estilos global
   - Após criar o QApplication, aplicar o stylesheet:
     ```python
     app.setStyleSheet("QMainWindow { background: transparent; }")
     ```
   - Isto mantém a coerência visual em janelas subsequentes.

---

## 4. Fluxo de arranque

```python
from PySide6.QtWidgets import QApplication
from ui.splashscreen import SplashScreen
import sys

app = QApplication(sys.argv)
splash = SplashScreen()
splash.show()

def continue_after_click():
    splash.close()
    from ui.mainwindow import MainWindow
    win = MainWindow()
    win.show()

splash.clicked.connect(continue_after_click)
app.exec()
```

### Observações
- A janela principal só abre quando o utilizador clicar na imagem.
- Durante operações demoradas, pode mostrar mensagem no splash e processar eventos:
  ```python
  splash.label.setText("A carregar base de dados...")
  app.processEvents()
  ```

---

## 5. Ambiente transparente em toda a aplicação

Para aplicar transparência global:
```python
from PySide6.QtCore import Qt
app.setAttribute(Qt.AA_TranslucentBackground, True)
```
E definir estilo global:
```css
QMainWindow, QWidget {
    background: transparent;
}
```
Certificar-se de que não há widgets com fundo sólido.

---

## 6. Bootstrap Qt

Adicionar no topo do main (ou bwb-fichas_tecnicas.py):
```python
import qt_bootstrap  # noqa: F401
```

Isto assegura:
- QT_QPA_PLATFORM_PLUGIN_PATH correto.
- Plugins de rendering (xcb, cocoa, etc.) carregados.
- Evita o erro “could not load the Qt platform plugin”.

---

## 7. Passos para replicar noutro projeto

1. Copiar ui/splashscreen.py e a imagem bwb-Splash.png.
2. Adaptar dimensões e nome conforme necessário.
3. Adicionar o import qt_bootstrap no entrypoint.
4. Aplicar folha de estilos global com background: transparent.
5. No arranque, conectar o sinal clicked à função que abre a janela principal.
6. Testar em macOS, Windows e Linux para garantir transparência e clique.

---

## 8. Comportamento esperado

- Ao iniciar, o utilizador vê a imagem splash (com transparência real).
- A aplicação espera pelo clique na imagem.
- Após o clique, o splash fecha e a janela principal abre.
- Transparências e temas mantêm-se ativos.

---

## 9. Verificação Codex

O Codex deve:
- Implementar ui/splashscreen.py e integrá-lo no app_launcher.py ou main.py.
- Garantir imagem PNG com canal alfa.
- Confirmar tratamento do evento de clique.
- Confirmar aplicação de Qt.WA_TranslucentBackground.
- Garantir stylesheet coerente com transparência.

---

**Fim do documento — Guia para replicação do Splash Screen clicável com fundo transparente.**

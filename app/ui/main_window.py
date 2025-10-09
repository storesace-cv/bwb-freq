"""Main window for the requisitions UI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.data.db import init_db
from app.ui.assets import BACKGROUND_IMAGE
from app.ui.background_utils import BackgroundLayer, ensure_transparent


MENU_STYLESHEET = """
QMenu {
    background-color: rgba(245, 222, 179, 160);
    border: 1px solid rgba(189, 183, 107, 180);
    border-radius: 12px;
    padding: 6px;
}

QMenu::item {
    background-color: transparent;
    border-radius: 8px;
    padding: 6px 20px;
    color: #202020;
}

QMenu::item:selected {
    background-color: rgba(255, 255, 255, 90);
}

QMenu::separator {
    height: 1px;
    background: rgba(0, 0, 0, 40);
    margin: 4px 0;
}
"""


class MainWindow(QMainWindow):
    """Minimal main window that exposes a menu button."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Requisições Internas — MVP")
        self.setFixedSize(1024, 768)
        self.setStyleSheet(
            "QMainWindow, #central-widget { background: transparent; }"
        )
        ensure_transparent(self)
        self._background_layer = BackgroundLayer(
            self,
            BACKGROUND_IMAGE,
            "main-background",
        )
        # Keep a direct reference to the QLabel created by ``BackgroundLayer``
        # so resize handlers can operate on ``_background_label`` as expected.
        self._background_label = self._background_layer.label
        init_db()

        central = QWidget(self)
        central.setObjectName("central-widget")
        ensure_transparent(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addStretch()

        self.menu_button = QToolButton(self)
        self.menu_button.setText("Menu")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        ensure_transparent(self.menu_button)
        size_hint = self.menu_button.sizeHint()
        self.menu_button.setFixedSize(size_hint.width() * 2, size_hint.height() * 2)
        self.menu_button.setStyleSheet(
            "QToolButton { font-size: 18px; padding: 8px 24px; border: none; }"
        )
        top_row.addWidget(self.menu_button)
        top_row.addSpacing(100)

        layout.addLayout(top_row)
        layout.addStretch(1)

        self.setCentralWidget(central)

        self._configure_menu()
        self._background_label.resize(self.size())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._background_label.resize(self.size())

    def _configure_menu(self) -> None:
        menu = QMenu(self.menu_button)
        self._apply_menu_styling(menu)

        base_de_dados_menu = menu.addMenu("Base de Dados")
        self._apply_menu_styling(base_de_dados_menu)
        base_de_dados_menu.addAction("Atualizar Dados")
        base_de_dados_menu.addAction("Importar Dados")
        seguranca_menu = base_de_dados_menu.addMenu("Segurança")
        self._apply_menu_styling(seguranca_menu)
        seguranca_menu.addAction("Segurança")
        seguranca_menu.addAction("Reposição")

        tabelas_menu = menu.addMenu("Tabelas")
        self._apply_menu_styling(tabelas_menu)
        tabelas_menu.addAction("Tipos Artigos")

        utilitarios_menu = menu.addMenu("Utilitários")
        self._apply_menu_styling(utilitarios_menu)
        gestao_documentos_menu = utilitarios_menu.addMenu("Gestão de Documentos")
        self._apply_menu_styling(gestao_documentos_menu)
        gestao_documentos_menu.addAction("Editor de Documentos")
        gestao_documentos_menu.addAction("Modelos Activos")
        gestao_documentos_menu.addAction("Actualizar Documentos")

        configuracoes_menu = menu.addMenu("Configurações")
        self._apply_menu_styling(configuracoes_menu)

        parametrizacoes_menu = menu.addMenu("Parametrizações")
        self._apply_menu_styling(parametrizacoes_menu)
        integracao_menu = parametrizacoes_menu.addMenu("Integração")
        self._apply_menu_styling(integracao_menu)
        integracao_menu.addAction("NETbo (Excel)")
        integracao_menu.addAction("NETbo (API)")
        integracao_menu.addAction("StoresAce (Excel)")
        parametrizacoes_menu.addAction("Moeda")

        self.menu_button.setMenu(menu)

    def _apply_menu_styling(self, menu: QMenu) -> None:
        """Apply the shared stylesheet for beige semi-transparent menus."""

        menu.setStyleSheet(MENU_STYLESHEET)

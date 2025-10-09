"""Main window for the requisitions UI."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.data.db import init_db
from app.ui.assets import BACKGROUND_IMAGE
from app.ui.background_utils import BackgroundLayer, ensure_transparent
from app.services.importer import (
    build_warehouse_articles_from_disp,
    import_article_barcodes,
    import_netbo_articles,
    import_wharehouses,
)


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
        scale_factor = 1.4  # 30% smaller than the previous doubled size
        self.menu_button.setFixedSize(
            int(size_hint.width() * scale_factor),
            int(size_hint.height() * scale_factor),
        )
        self.menu_button.setStyleSheet(
            "QToolButton { font-size: 16px; padding: 6px 18px; border: none; }"
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
        importar_dados_action = base_de_dados_menu.addAction("Importar Dados")
        importar_dados_action.triggered.connect(self._import_incoming_excels)
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

    def _import_incoming_excels(self) -> None:
        """Import Excel files from ``imports/incoming`` and archive them."""

        incoming_dir = Path("imports/incoming")
        processed_dir = Path("imports/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)

        tasks = (
            ("netbo_articles.xlsx", import_netbo_articles, "NetboArticles"),
            ("Lojas e Armazens.xlsx", import_wharehouses, "Wharehouses"),
            ("article_barcodes.xlsx", import_article_barcodes, "ArticleBarcodes"),
        )

        imported = []
        missing = []
        errors = []

        for file_name, importer, label in tasks:
            src = incoming_dir / file_name
            if not src.exists():
                missing.append(file_name)
                continue

            try:
                rows = importer(str(src))
            except Exception as exc:  # pragma: no cover - user interaction
                errors.append(f"{file_name}: {exc}")
                continue

            dest = processed_dir / file_name
            if dest.exists():
                dest.unlink()
            src.replace(dest)
            imported.append(f"{label}: {rows} linhas")

        if imported:
            try:
                build_warehouse_articles_from_disp()
            except Exception as exc:  # pragma: no cover - user interaction
                errors.append(f"WarehouseArticles: {exc}")

        if errors:
            message = "Ocorreram erros ao importar:\n" + "\n".join(errors)
            if imported:
                message += "\n\nImportações concluídas:\n" + "\n".join(imported)
            if missing:
                message += "\n\nFicheiros em falta:\n" + "\n".join(missing)
            QMessageBox.critical(self, "Importação com erros", message)
            return

        if not imported:
            if missing:
                message = (
                    "Não foram encontrados ficheiros para importar.\n\n"
                    "Esperados:\n" + "\n".join(missing)
                )
            else:
                message = "Não existem ficheiros para importar em imports/incoming."
            QMessageBox.information(self, "Sem dados", message)
            return

        message_lines = ["Importação concluída com sucesso:"] + imported
        if missing:
            message_lines.append("\nFicheiros em falta:")
            message_lines.extend(missing)
        QMessageBox.information(self, "Importação concluída", "\n".join(message_lines))

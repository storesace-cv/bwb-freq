"""Main window for the requisitions UI."""

from io import BytesIO
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from barcode import get_barcode_class
from barcode.writer import ImageWriter

from app.data.db import get_connection, init_db
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

        self.workspace = QWidget(self)
        ensure_transparent(self.workspace)
        self.workspace_layout = QVBoxLayout(self.workspace)
        self.workspace_layout.setContentsMargins(32, 24, 32, 32)
        self.workspace_layout.setSpacing(16)

        self.workspace_hint_default_text = (
            "Selecione uma tabela em Tabelas para visualizar os dados."
        )
        self.workspace_hint = QLabel(
            self.workspace_hint_default_text,
            self.workspace,
        )
        self.workspace_hint.setAlignment(Qt.AlignCenter)
        self.workspace_hint.setStyleSheet("color: #202020; font-size: 16px;")
        self.workspace_layout.addWidget(self.workspace_hint, alignment=Qt.AlignCenter)

        self.table_widget = QTableWidget(self.workspace)
        self.table_widget.setVisible(False)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setWordWrap(False)
        self.table_widget.setTextElideMode(Qt.ElideRight)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setStretchLastSection(False)
        self.workspace_layout.addWidget(self.table_widget)

        layout.addWidget(self.workspace, stretch=1)

        self.setCentralWidget(central)

        self._barcode_pixmap_cache: dict[str, QPixmap] = {}

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
        artigos_action = tabelas_menu.addAction("Artigos")
        artigos_action.triggered.connect(self._show_netbo_articles)
        departamentos_action = tabelas_menu.addAction("Departamentos")
        departamentos_action.triggered.connect(self._show_wharehouses)
        barcodes_action = tabelas_menu.addAction("Artigos | Códigos de Barras")
        barcodes_action.triggered.connect(self._show_article_barcodes)

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

    def _show_netbo_articles(self) -> None:
        """Display NetboArticles table with custom column sizing."""

        columns = (
            "Codigo",
            "Produto",
            "Familia",
            "SubFamilia",
            "Unidade",
            "UnVenda",
            "UnInventario",
            "UnProducao",
        )
        query = (
            "SELECT Codigo, Produto, Familia, SubFamilia, Unidade, "
            "UnVenda, UnInventario, UnProducao FROM NetboArticles"
        )
        rows = self._fetch_rows(query)
        self._populate_table(columns, rows, table_kind="netbo")

    def _show_wharehouses(self) -> None:
        """Display Wharehouses table with auto-sized columns."""

        columns = (
            "Codigo",
            "Tipo",
            "Nome",
            "Nif",
            "TipoFo",
            "EmailDoResponsavel",
        )
        query = (
            "SELECT Codigo, Tipo, Nome, Nif, TipoFo, EmailDoResponsavel FROM Wharehouses"
        )
        rows = self._fetch_rows(query)
        self._populate_table(columns, rows, table_kind="wharehouses")

    def _show_article_barcodes(self) -> None:
        """Display ArticleBarcodes table with auto-sized columns."""

        columns = (
            "ArticleFoId",
            "ArticleName",
            "Barcode",
            "UnidadeName",
            "Código de Barras (Imagem)",
        )
        query = (
            "SELECT ArticleFoId, ArticleName, Barcode, UnidadeName FROM ArticleBarcodes"
        )
        rows = self._fetch_rows(query)
        self._populate_table(columns, rows, table_kind="barcodes")

    def _fetch_rows(self, query: str) -> list:
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def _populate_table(self, columns: tuple[str, ...], rows: list, *, table_kind: str) -> None:
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)
        self.table_widget.setRowCount(len(rows))

        barcode_image_header = "Código de Barras (Imagem)"
        barcode_column_index = columns.index("Barcode") if "Barcode" in columns else None

        for row_index, row in enumerate(rows):
            barcode_value = None
            if barcode_column_index is not None:
                barcode_value = self._get_row_value(row, "Barcode", barcode_column_index)

            for col_index, column in enumerate(columns):
                if table_kind == "barcodes" and column == barcode_image_header:
                    self._set_barcode_cell(row_index, col_index, barcode_value)
                    continue

                value = self._get_row_value(row, column, col_index)
                text = "" if value is None else str(value)
                item = QTableWidgetItem()
                display_text = text

                if column in {"Familia", "SubFamilia"}:
                    truncated, tooltip = self._truncate_with_tooltip(text, 20)
                    display_text = truncated
                    if tooltip:
                        item.setToolTip(tooltip)
                elif column == "Produto":
                    if text:
                        item.setToolTip(text)
                else:
                    if text and column in {"ArticleName", "Barcode", "UnidadeName"}:
                        item.setToolTip(text)

                item.setText(display_text)
                self.table_widget.setItem(row_index, col_index, item)

        if not rows:
            self.table_widget.setRowCount(0)

        self._configure_header(columns, table_kind)
        self.table_widget.setVisible(True)
        if rows:
            self.workspace_hint.setVisible(False)
            self.workspace_hint.setText(self.workspace_hint_default_text)
        else:
            self.workspace_hint.setText("Não existem registos para mostrar.")
            self.workspace_hint.setVisible(True)

    def _configure_header(self, columns: tuple[str, ...], table_kind: str) -> None:
        header = self.table_widget.horizontalHeader()
        header.setStretchLastSection(False)

        if table_kind == "netbo":
            product_index = columns.index("Produto")
            familia_index = columns.index("Familia")
            subfamilia_index = columns.index("SubFamilia")

            char_width = self.table_widget.fontMetrics().horizontalAdvance("W")
            familia_width = char_width * 20 + 16

            for index, column in enumerate(columns):
                if index == product_index:
                    header.setSectionResizeMode(index, QHeaderView.Stretch)
                elif index in {familia_index, subfamilia_index}:
                    header.setSectionResizeMode(index, QHeaderView.Fixed)
                    header.resizeSection(index, familia_width)
                else:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        elif table_kind == "barcodes":
            barcode_image_header = "Código de Barras (Imagem)"
            barcode_image_index = columns.index(barcode_image_header)

            for index, _ in enumerate(columns):
                if index == barcode_image_index:
                    header.setSectionResizeMode(index, QHeaderView.Stretch)
                    self.table_widget.setColumnMinimumWidth(index, 220)
                else:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        else:
            for index, _ in enumerate(columns):
                header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)

    def _truncate_with_tooltip(self, text: str, limit: int) -> tuple[str, str | None]:
        if not text:
            return "", None
        if len(text) <= limit:
            return text, None
        truncated = text[:limit].rstrip()
        return f"{truncated}…", text

    def _get_row_value(self, row, column: str, index: int):
        if hasattr(row, "keys"):
            try:
                return row[column]
            except (KeyError, TypeError):
                return None
        if index < len(row):
            return row[index]
        return None

    def _set_barcode_cell(
        self, row_index: int, col_index: int, barcode_value: str | None
    ) -> None:
        label = QLabel(self.table_widget)
        label.setAlignment(Qt.AlignCenter)

        pixmap = self._get_barcode_pixmap(barcode_value)
        if pixmap is not None:
            scaled = pixmap.scaledToHeight(64, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.setToolTip(barcode_value or "")
            current_height = self.table_widget.rowHeight(row_index)
            desired_height = scaled.height() + 8
            if desired_height > current_height:
                self.table_widget.setRowHeight(row_index, desired_height)
        else:
            label.setText("—")
            if barcode_value:
                label.setToolTip(barcode_value)

        placeholder = QTableWidgetItem()
        placeholder.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        placeholder.setText("")
        self.table_widget.setItem(row_index, col_index, placeholder)
        self.table_widget.setCellWidget(row_index, col_index, label)

    def _get_barcode_pixmap(self, barcode_value: str | None) -> QPixmap | None:
        if not barcode_value:
            return None
        if barcode_value in self._barcode_pixmap_cache:
            return self._barcode_pixmap_cache[barcode_value]

        try:
            barcode_class = get_barcode_class("code128")
            barcode = barcode_class(barcode_value, writer=ImageWriter())
            buffer = BytesIO()
            barcode.write(
                buffer,
                {
                    "module_height": 40.0,
                    "module_width": 0.2,
                    "quiet_zone": 2.0,
                    "font_size": 10,
                },
            )
            pixmap = QPixmap()
            if pixmap.loadFromData(buffer.getvalue()):
                self._barcode_pixmap_cache[barcode_value] = pixmap
                return pixmap
        except Exception:  # pragma: no cover - fallback for invalid barcodes
            return None
        return None

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

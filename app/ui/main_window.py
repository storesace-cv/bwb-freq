"""Main window for the requisitions UI."""

from dataclasses import dataclass
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Callable

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
    QSizePolicy,
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


@dataclass(frozen=True)
class TableDisplayConfig:
    """Immutable configuration describing how to render a database table."""

    columns: tuple[str, ...]
    query: str
    table_kind: str


TABLE_CONFIGS: dict[str, TableDisplayConfig] = {
    "netbo": TableDisplayConfig(
        columns=(
            "Codigo",
            "Produto",
            "Familia",
            "SubFamilia",
            "Unidade",
            "UnVenda",
            "UnInventario",
            "UnProducao",
        ),
        query=(
            "SELECT Codigo, Produto, Familia, SubFamilia, Unidade, "
            "UnVenda, UnInventario, UnProducao FROM NetboArticles"
        ),
        table_kind="netbo",
    ),
    "wharehouses": TableDisplayConfig(
        columns=(
            "Codigo",
            "Tipo",
            "Nome",
            "Nif",
            "TipoFo",
            "EmailDoResponsavel",
        ),
        query=(
            "SELECT Codigo, Tipo, Nome, Nif, TipoFo, EmailDoResponsavel FROM Wharehouses"
        ),
        table_kind="wharehouses",
    ),
    "barcodes": TableDisplayConfig(
        columns=(
            "ArticleFoId",
            "ArticleName",
            "Barcode",
            "UnidadeName",
            "Código de Barras (Imagem)",
            "Tipo de Código de Barras",
        ),
        query=(
            "SELECT ArticleFoId, ArticleName, Barcode, UnidadeName FROM ArticleBarcodes"
        ),
        table_kind="barcodes",
    ),
}


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
        header = self.table_widget.horizontalHeader()
        header.setStretchLastSection(False)
        header.sectionResized.connect(self._handle_section_resized)
        self.workspace_layout.addWidget(self.table_widget)

        layout.addWidget(self.workspace, stretch=1)

        self.setCentralWidget(central)

        self._barcode_pixmap_cache: dict[str, QPixmap] = {}
        self._barcode_image_max_width: int = 0
        self._barcode_label_entries: list[tuple[int, QLabel]] = []
        self._barcode_image_column: int | None = None

        self._configure_menu()
        self._background_label.resize(self.size())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._background_label.resize(self.size())

    def _configure_menu(self) -> None:
        menu = QMenu(self.menu_button)
        self._apply_menu_styling(menu)

        base_de_dados_menu = self._add_submenu(menu, "Base de Dados")
        self._add_action(base_de_dados_menu, "Atualizar Dados")
        self._add_action(
            base_de_dados_menu,
            "Importar Dados",
            handler=self._import_incoming_excels,
        )
        seguranca_menu = self._add_submenu(base_de_dados_menu, "Segurança")
        self._add_action(seguranca_menu, "Segurança")
        self._add_action(seguranca_menu, "Reposição")

        tabelas_menu = self._add_submenu(menu, "Tabelas")
        self._add_action(
            tabelas_menu,
            "Artigos",
            handler=partial(self._show_table, "netbo"),
        )
        self._add_action(
            tabelas_menu,
            "Departamentos",
            handler=partial(self._show_table, "wharehouses"),
        )
        self._add_action(
            tabelas_menu,
            "Artigos | Códigos de Barras",
            handler=partial(self._show_table, "barcodes"),
        )

        utilitarios_menu = self._add_submenu(menu, "Utilitários")
        gestao_documentos_menu = self._add_submenu(
            utilitarios_menu, "Gestão de Documentos"
        )
        self._add_action(gestao_documentos_menu, "Editor de Documentos")
        self._add_action(gestao_documentos_menu, "Modelos Activos")
        self._add_action(gestao_documentos_menu, "Actualizar Documentos")

        self._add_submenu(menu, "Configurações")

        parametrizacoes_menu = self._add_submenu(menu, "Parametrizações")
        integracao_menu = self._add_submenu(parametrizacoes_menu, "Integração")
        self._add_action(integracao_menu, "NETbo (Excel)")
        self._add_action(integracao_menu, "NETbo (API)")
        self._add_action(integracao_menu, "StoresAce (Excel)")
        self._add_action(parametrizacoes_menu, "Moeda")

        self.menu_button.setMenu(menu)

    def _add_submenu(self, parent: QMenu, title: str) -> QMenu:
        """Create a submenu and ensure the shared style is applied."""

        submenu = parent.addMenu(title)
        self._apply_menu_styling(submenu)
        return submenu

    def _add_action(
        self, menu: QMenu, title: str, *, handler: Callable[[], None] | None = None
    ):
        """Create an action and connect it to ``handler`` when provided."""

        action = menu.addAction(title)
        if handler is not None:
            action.triggered.connect(partial(self._invoke_action_handler, handler))
        return action

    def _invoke_action_handler(
        self, handler: Callable[[], None], _checked: bool = False
    ) -> None:
        """Invoke ``handler`` ignoring the checked state from Qt signals."""

        handler()

    def _apply_menu_styling(self, menu: QMenu) -> None:
        """Apply the shared stylesheet for beige semi-transparent menus."""

        menu.setStyleSheet(MENU_STYLESHEET)

    def _show_table(self, table_id: str) -> None:
        """Fetch the configuration for ``table_id`` and display the rows."""

        config = TABLE_CONFIGS.get(table_id)
        if config is None:
            raise ValueError(f"Unknown table identifier: {table_id}")

        rows = self._fetch_rows(config.query)
        self._populate_table(config.columns, rows, table_kind=config.table_kind)

    def _fetch_rows(self, query: str) -> list:
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def _populate_table(self, columns: tuple[str, ...], rows: list, *, table_kind: str) -> None:
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)
        self.table_widget.setRowCount(len(rows))

        barcode_image_header = "Código de Barras (Imagem)"
        barcode_type_header = "Tipo de Código de Barras"
        barcode_column_index = columns.index("Barcode") if "Barcode" in columns else None

        self._barcode_label_entries = []

        if table_kind == "barcodes":
            self._barcode_image_max_width = 0

        for row_index, row in enumerate(rows):
            barcode_value = None
            if barcode_column_index is not None:
                barcode_value = self._get_row_value(row, "Barcode", barcode_column_index)
            barcode_type = (
                self._infer_barcode_type(barcode_value)
                if table_kind == "barcodes"
                else None
            )

            for col_index, column in enumerate(columns):
                if table_kind == "barcodes" and column == barcode_image_header:
                    width = self._set_barcode_cell(row_index, col_index, barcode_value)
                    if width:
                        self._barcode_image_max_width = max(
                            self._barcode_image_max_width, width
                        )
                    continue
                if table_kind == "barcodes" and column == barcode_type_header:
                    display_type = barcode_type or "-N/A-"
                    item = QTableWidgetItem(display_type)
                    if barcode_type:
                        item.setToolTip(barcode_type)
                    self.table_widget.setItem(row_index, col_index, item)
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
            barcode_type_header = "Tipo de Código de Barras"
            barcode_image_index = columns.index(barcode_image_header)
            barcode_type_index = columns.index(barcode_type_header)

            for index, _ in enumerate(columns):
                if index == barcode_image_index:
                    header.setSectionResizeMode(index, QHeaderView.Interactive)
                    minimum_width = max(self._barcode_image_max_width + 24, 220)
                    self.table_widget.setColumnMinimumWidth(index, minimum_width)
                    header.resizeSection(index, minimum_width)
                elif index == barcode_type_index:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
                else:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
            self._barcode_image_column = barcode_image_index
            self._resize_barcode_images(barcode_image_index)
        else:
            for index, _ in enumerate(columns):
                header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
            self._barcode_image_column = None

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

    def _infer_barcode_type(self, barcode_value: str | None) -> str | None:
        if not barcode_value:
            return None

        digits = barcode_value.strip()
        if not digits.isdigit():
            return None

        length = len(digits)
        if length == 13:
            return "EAN-13"
        if length == 12:
            return "UPC-A"
        if length == 8:
            if self._looks_like_upc_e(digits):
                return "UPC-E"
            return "EAN-8"

        return None

    def _looks_like_upc_e(self, digits: str) -> bool:
        if len(digits) != 8 or not digits.isdigit():
            return False
        if digits[0] not in {"0", "1"}:
            return False

        data = digits[1:7]
        last = data[-1]

        if last in {"0", "1", "2"}:
            manufacturer = data[:2] + last
            product = "00" + data[2:5]
        elif last == "3":
            manufacturer = data[:3]
            product = "000" + data[3:5]
        elif last == "4":
            manufacturer = data[:4]
            product = "0000" + data[4]
        else:
            manufacturer = data[:5]
            product = "0000" + last

        return len(manufacturer) == 5 and len(product) == 5

    def _set_barcode_cell(
        self, row_index: int, col_index: int, barcode_value: str | None
    ) -> int | None:
        label = QLabel(self.table_widget)
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        pixmap = self._get_barcode_pixmap(barcode_value)
        if pixmap is not None:
            scaled = pixmap.scaledToHeight(64, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.setToolTip(barcode_value or "")
            label.setMinimumHeight(scaled.height())
            label.setMinimumWidth(scaled.width())
            label._orig_pixmap = pixmap  # type: ignore[attr-defined]
            self._barcode_label_entries.append((row_index, label))
            current_height = self.table_widget.rowHeight(row_index)
            desired_height = scaled.height() + 8
            if desired_height > current_height:
                self.table_widget.setRowHeight(row_index, desired_height)
            width = scaled.width()
        else:
            label.setText("—")
            if barcode_value:
                label.setToolTip(barcode_value)
            width = None

        placeholder = QTableWidgetItem()
        placeholder.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        placeholder.setText("")
        self.table_widget.setItem(row_index, col_index, placeholder)
        self.table_widget.setCellWidget(row_index, col_index, label)
        return width

    def _resize_barcode_images(self, column_index: int) -> None:
        if not self._barcode_label_entries:
            return

        available_width = max(self.table_widget.columnWidth(column_index) - 12, 1)
        for row_index, label in self._barcode_label_entries:
            pixmap = getattr(label, "_orig_pixmap", None)
            if not isinstance(pixmap, QPixmap) or pixmap.isNull():
                continue

            scaled = pixmap.scaled(
                available_width,
                96,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            label.setPixmap(scaled)
            label.setMinimumWidth(scaled.width())
            label.setMinimumHeight(scaled.height())

            desired_height = scaled.height() + 8
            if self.table_widget.rowHeight(row_index) < desired_height:
                self.table_widget.setRowHeight(row_index, desired_height)

    def _handle_section_resized(self, logical_index: int, _old_size: int, _new_size: int) -> None:
        if self._barcode_image_column == logical_index:
            self._resize_barcode_images(logical_index)

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

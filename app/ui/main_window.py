"""Main window for the requisitions UI."""

from dataclasses import dataclass
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
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
from app.services.importer import (
    build_warehouse_articles_from_disp,
    import_article_barcodes,
    import_fichas_tecnicas,
    import_netbo_articles,
    import_wharehouses,
)
from app.ui.assets import APP_ICON
from app.utils.barcodes import classify_gs1_barcode


@dataclass(frozen=True)
class TableDisplayConfig:
    """Immutable configuration describing how to render a database table."""

    columns: tuple[str, ...]
    query: str
    table_kind: str


BARCODE_DISPLAY_LIMIT = 14


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
        ),
        query=(
            "SELECT ArticleFoId, ArticleName, Barcode, UnidadeName FROM ArticleBarcodes"
        ),
        table_kind="barcodes",
    ),
    "fichas_tecnicas": TableDisplayConfig(
        columns=(
            "ProdVendaGenerico",
            "Componente",
            "Quantidade",
            "Unidade",
        ),
        query=(
            "SELECT ProdVendaGenerico, Componente, Quantidade, Unidade FROM FichasTecnicas"
        ),
        table_kind="fichas_tecnicas",
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
        if APP_ICON.exists():
            self.setWindowIcon(QIcon(str(APP_ICON)))
        self.setFixedSize(1024, 768)
        self.setStyleSheet(
            "QMainWindow { background-color: rgba(245, 245, 245, 242); }"
            "#central-widget { background-color: rgba(255, 255, 255, 242); }"
            "QTableWidget {"
            "    background-color: rgba(255, 255, 255, 242);"
            "    alternate-background-color: rgba(240, 240, 240, 242);"
            "    gridline-color: #d0d0d0;"
            "}"
        )
        init_db()

        central = QWidget(self)
        central.setObjectName("central-widget")

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addStretch()

        self.menu_button = QToolButton(self)
        self.menu_button.setText("Menu")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
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
        self.workspace_layout.addWidget(self.table_widget)

        layout.addWidget(self.workspace, stretch=1)

        self.setCentralWidget(central)

        self._barcode_pixmap_cache: dict[str, QPixmap] = {}
        self._open_barcode_previews: list[QDialog] = []

        self._configure_menu()

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
        self._add_action(
            tabelas_menu,
            "Artigos | Fichas Técnicas",
            handler=partial(self._show_table, "fichas_tecnicas"),
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

        barcode_column_index = columns.index("Barcode") if "Barcode" in columns else None

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
                if table_kind == "barcodes" and column == "Barcode":
                    self._set_barcode_cell(
                        row_index,
                        col_index,
                        barcode_value,
                        barcode_type,
                    )
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
        self.table_widget.viewport().update()
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
            barcode_index = columns.index("Barcode")
            char_width = self.table_widget.fontMetrics().horizontalAdvance("0")
            barcode_width = char_width * BARCODE_DISPLAY_LIMIT + 24

            for index, _ in enumerate(columns):
                if index == barcode_index:
                    header.setSectionResizeMode(index, QHeaderView.Fixed)
                    header.resizeSection(index, barcode_width)
                else:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
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

    def _infer_barcode_type(self, barcode_value: str | None) -> str | None:
        if not barcode_value:
            return None

        barcode_type = classify_gs1_barcode(barcode_value)
        friendly_labels = {
            "EAN13": "EAN-13",
            "EAN8": "EAN-8",
            "UPCA": "UPC-A",
            "UPCE": "UPC-E",
            "GTIN14": "GTIN-14",
            "GS1-128": "GS1-128",
            "GS1DataBar": "GS1 DataBar",
            "SSCC": "SSCC",
            "Code128": "Code128",
        }
        label = friendly_labels.get(barcode_type)
        if label == "Code128" and not barcode_value.strip():
            return None
        return label

    def _set_barcode_cell(
        self,
        row_index: int,
        col_index: int,
        barcode_value: str | None,
        barcode_type: str | None,
    ) -> None:
        display_text = barcode_value or ""
        tooltip_text = None

        if barcode_value:
            display_text, tooltip_text = self._truncate_with_tooltip(
                barcode_value, BARCODE_DISPLAY_LIMIT
            )
            if tooltip_text is None:
                tooltip_text = barcode_value

        item = QTableWidgetItem(display_text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if tooltip_text:
            item.setToolTip(tooltip_text)
        self.table_widget.setItem(row_index, col_index, item)

        container = QWidget(self.table_widget)
        container.setAutoFillBackground(False)

        layout = QGridLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(0)
        layout.setColumnStretch(0, 1)

        text_label = QLabel(display_text, container)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_label.setWordWrap(False)
        if tooltip_text:
            text_label.setToolTip(tooltip_text)
        layout.addWidget(text_label, 0, 0, alignment=Qt.AlignVCenter | Qt.AlignLeft)

        eye_button = QToolButton(container)
        eye_button.setAutoRaise(True)
        eye_button.setCursor(Qt.PointingHandCursor)
        eye_button.setStyleSheet(
            "QToolButton { border: none; color: #c62828; font-size: 14px; padding: 0; }"
            "QToolButton::menu-indicator { image: none; }"
        )
        eye_button.setText("👁")
        eye_button.setToolTip("Ver código de barras")
        eye_button.setFixedSize(18, 18)

        if barcode_value:
            eye_button.clicked.connect(
                partial(self._show_barcode_preview, barcode_value, barcode_type)
            )
        else:
            eye_button.setEnabled(False)

        layout.addWidget(eye_button, 0, 1, alignment=Qt.AlignTop | Qt.AlignRight)

        self.table_widget.setCellWidget(row_index, col_index, container)

    def _show_barcode_preview(
        self, barcode_value: str, barcode_type: str | None = None
    ) -> None:
        if not barcode_value:
            QMessageBox.information(
                self,
                "Código de barras indisponível",
                "Não existe um código de barras para apresentar.",
            )
            return

        resolved_barcode_type = barcode_type or self._infer_barcode_type(barcode_value)
        pixmap = self._get_barcode_pixmap(barcode_value)
        if pixmap is None or pixmap.isNull():
            QMessageBox.warning(
                self,
                "Pré-visualização indisponível",
                "Não foi possível gerar a imagem do código de barras.",
            )
            return

        preview = QDialog(self)
        preview.setWindowTitle(f"Código de Barras — {barcode_value}")
        preview.setModal(False)
        preview.setAttribute(Qt.WA_DeleteOnClose, True)

        layout = QVBoxLayout(preview)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        preview_label = QLabel(preview)
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setToolTip(barcode_value)

        max_height = 220
        if pixmap.height() > max_height:
            scaled_pixmap = pixmap.scaledToHeight(
                max_height, Qt.SmoothTransformation
            )
        else:
            scaled_pixmap = pixmap

        preview_label.setPixmap(scaled_pixmap)
        layout.addWidget(preview_label)

        info_row = QWidget(preview)
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        type_label = QLabel(info_row)
        type_label.setText(
            f"Tipo: {resolved_barcode_type}" if resolved_barcode_type else "Tipo desconhecido"
        )
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet(
            "background-color: #1565c0; color: white; padding: 6px 10px;"
            "border-radius: 4px; font-size: 12px;"
        )
        type_label.setMinimumHeight(28)
        if resolved_barcode_type:
            type_label.setToolTip(resolved_barcode_type)
        info_layout.addWidget(type_label, stretch=1)

        printer_label = QLabel(info_row)
        printer_label.setText("🖨")
        printer_label.setAlignment(Qt.AlignCenter)
        printer_label.setStyleSheet(
            "background-color: #9e9e9e; color: white; padding: 6px 10px;"
            "border-radius: 4px; font-size: 14px;"
        )
        printer_label.setMinimumHeight(28)
        printer_label.setToolTip("Ações de impressão brevemente disponíveis")
        info_layout.addWidget(printer_label, stretch=1)

        layout.addWidget(info_row)

        preview.resize(max(scaled_pixmap.width() + 48, preview.sizeHint().width()), preview.sizeHint().height())
        self._open_barcode_previews.append(preview)

        def _cleanup_preview(_=None, dialog=preview) -> None:
            if dialog in self._open_barcode_previews:
                self._open_barcode_previews.remove(dialog)

        preview.destroyed.connect(_cleanup_preview)
        preview.show()

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
                    "module_width": 0.8,
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
            ("Fichas Tecnicas.xlsx", import_fichas_tecnicas, "FichasTecnicas"),
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

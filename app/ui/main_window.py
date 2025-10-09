"""Main window for the requisitions UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.data.db import get_connection, init_db
from app.services.printer import (
    ArticleFilter,
    build_print_context,
    export_context_json,
    export_csv_simple,
    filter_articles,
)


@dataclass(slots=True)
class Warehouse:
    codigo: str
    nome: str


class MainWindow(QMainWindow):
    """Simple GUI for selecting warehouses and exporting requisition data."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Requisições Internas — MVP")
        self.setFixedSize(1024, 768)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_NoBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        background_pixmap = QPixmap(
            str(Path(__file__).with_name("bwb-Splash-background.png"))
        )
        self._background_label = QLabel(self)
        self._background_label.setObjectName("main-background")
        self._background_label.setPixmap(background_pixmap)
        self._background_label.setScaledContents(True)
        self._background_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._background_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._background_label.setStyleSheet("background: transparent;")
        self._background_label.lower()
        init_db()

        self._warehouses: List[Warehouse] = []
        self._article_cache: Dict[str, List[dict]] = {}
        self._warehouse_totals: Dict[str, Dict[str, object]] = {}
        self._current_warehouse: Warehouse | None = None

        central = QWidget(self)
        central.setObjectName("central-widget")
        central.setAttribute(Qt.WA_TranslucentBackground, True)
        central.setAttribute(Qt.WA_StyledBackground, True)
        central.setAutoFillBackground(False)
        central.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        description = QLabel(
            "Selecione um ou mais armazéns para exportar os ficheiros JSON/CSV\n"
            "que alimentam o ReportBro (fase PDFs)."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.currentItemChanged.connect(self._on_current_warehouse_changed)
        layout.addWidget(self.list_widget)

        filters_row = QHBoxLayout()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Filtrar por código ou produto…")
        self.search_input.textChanged.connect(self._apply_filters)
        filters_row.addWidget(self.search_input, stretch=1)

        self.only_missing_checkbox = QCheckBox("Apenas sem código", self)
        self.only_missing_checkbox.toggled.connect(self._apply_filters)
        filters_row.addWidget(self.only_missing_checkbox)

        layout.addLayout(filters_row)

        self.apply_filters_checkbox = QCheckBox(
            "Aplicar filtros na exportação", self
        )
        layout.addWidget(self.apply_filters_checkbox)

        self.summary_label = QLabel(
            "Selecione um armazém para pré-visualizar os artigos.", self
        )
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.article_table = QTableWidget(self)
        self.article_table.setColumnCount(6)
        self.article_table.setHorizontalHeaderLabels(
            [
                "Código",
                "Produto",
                "Unidade",
                "Quantidade",
                "Código de Barras",
                "Tipo",
            ]
        )
        self.article_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.article_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.article_table.setAlternatingRowColors(True)
        self.article_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.article_table, stretch=1)

        self.export_selected_btn = QPushButton("Exportar selecionados", self)
        self.export_selected_btn.clicked.connect(self._export_selected)
        layout.addWidget(self.export_selected_btn)

        self.export_all_btn = QPushButton("Exportar todos", self)
        self.export_all_btn.clicked.connect(self._export_all)
        layout.addWidget(self.export_all_btn)

        self.refresh_btn = QPushButton("Atualizar lista", self)
        self.refresh_btn.clicked.connect(self.refresh_warehouses)
        layout.addWidget(self.refresh_btn)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.setCentralWidget(central)
        self.statusBar().setAttribute(Qt.WA_TranslucentBackground, True)
        self.statusBar().setStyleSheet("background: transparent;")

        self.refresh_warehouses()

        self._background_label.resize(self.size())

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._background_label.resize(self.size())

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def refresh_warehouses(self) -> None:
        """Load the list of warehouses from the database."""

        self._warehouses = self._fetch_warehouses()
        self._article_cache.clear()
        self._warehouse_totals.clear()
        self._current_warehouse = None
        self.list_widget.clear()
        for wh in self._warehouses:
            item = QListWidgetItem(f"{wh.codigo} — {wh.nome}")
            item.setData(Qt.UserRole, wh)
            self.list_widget.addItem(item)
        if self._warehouses:
            self.list_widget.setCurrentRow(0)
        else:
            self.article_table.setRowCount(0)
            self.summary_label.setText(
                "Nenhum armazém disponível. Importe dados antes de continuar."
            )
        self.status_bar.showMessage(
            f"Armazéns disponíveis: {len(self._warehouses)}",
            5000,
        )

    def _fetch_warehouses(self) -> List[Warehouse]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT Codigo, Nome FROM Wharehouses ORDER BY Codigo"
            ).fetchall()
        return [Warehouse(codigo=row["Codigo"], nome=row["Nome"]) for row in rows]

    def _on_current_warehouse_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            self._current_warehouse = None
            self.article_table.setRowCount(0)
            self.summary_label.setText(
                "Selecione um armazém para pré-visualizar os artigos."
            )
            return

        warehouse: Warehouse = current.data(Qt.UserRole)
        self._current_warehouse = warehouse
        self._load_articles_for(warehouse)

    def _load_articles_for(self, warehouse: Warehouse) -> None:
        try:
            context = build_print_context(warehouse.codigo)
        except Exception as exc:  # pragma: no cover - error path
            QMessageBox.warning(
                self,
                "Erro ao carregar",
                f"Falha ao carregar artigos para {warehouse.codigo}: {exc}",
            )
            self.article_table.setRowCount(0)
            self.summary_label.setText(
                "Não foi possível carregar os artigos do armazém selecionado."
            )
            return

        artigos = context["artigos"]
        self._article_cache[warehouse.codigo] = artigos
        self._warehouse_totals[warehouse.codigo] = {
            "total": len(artigos),
            "missing": sum(1 for a in artigos if not a["barcode_value"]),
            "nome": context["warehouse"]["Nome"],
        }

        self.status_bar.showMessage(
            (
                f"{warehouse.codigo} — {context['warehouse']['Nome']}: "
                f"{len(artigos)} artigos (sem código: "
                f"{self._warehouse_totals[warehouse.codigo]['missing']})"
            ),
            5000,
        )
        self._apply_filters()

    def _current_article_filter(self) -> ArticleFilter:
        return ArticleFilter(
            text=self.search_input.text(),
            only_missing_barcodes=self.only_missing_checkbox.isChecked(),
        )

    def _apply_filters(self) -> None:
        if self._current_warehouse is None:
            return

        codigo = self._current_warehouse.codigo
        artigos = self._article_cache.get(codigo, [])
        article_filter = self._current_article_filter()
        filtered = filter_articles(artigos, article_filter)

        self.article_table.setRowCount(len(filtered))
        for row, artigo in enumerate(filtered):
            self._set_row(row, artigo)

        total = self._warehouse_totals.get(codigo, {}).get("total", len(artigos))
        total_missing = self._warehouse_totals.get(codigo, {}).get("missing", 0)
        filtered_missing = sum(1 for a in filtered if not a["barcode_value"])
        summary_text = (
            f"{len(filtered)} de {total} artigos visíveis — sem código: {filtered_missing}"
        )
        if total_missing and total_missing != filtered_missing:
            summary_text += f" (total sem código: {total_missing})"
        self.summary_label.setText(summary_text)

    def _set_row(self, row: int, artigo: dict) -> None:
        values = [
            artigo.get("Codigo", ""),
            artigo.get("Produto", ""),
            artigo.get("Unidade", ""),
            artigo.get("Quantidade", ""),
            artigo.get("barcode_value", "") or "",
            artigo.get("barcode_type", "") or "",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.article_table.setItem(row, column, item)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    def _ask_output_dir(self) -> Path | None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Selecionar diretório de saída",
            str(Path.cwd() / "out"),
        )
        if not directory:
            return None
        return Path(directory)

    def _export_selected(self) -> None:
        warehouses = [item.data(Qt.UserRole) for item in self.list_widget.selectedItems()]
        self._export_warehouses(warehouses)

    def _export_all(self) -> None:
        self._export_warehouses(self._warehouses)

    def _export_warehouses(self, warehouses: Iterable[Warehouse]) -> None:
        warehouses = list(warehouses)
        if not warehouses:
            QMessageBox.information(self, "Exportação", "Nenhum armazém selecionado.")
            return
        output_dir = self._ask_output_dir()
        if output_dir is None:
            return
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
        filters = self._current_article_filter() if self.apply_filters_checkbox.isChecked() else None
        for wh in warehouses:
            try:
                export_context_json(
                    wh.codigo,
                    str(output_dir / f"{wh.codigo}.json"),
                    filters=filters,
                )
                export_csv_simple(
                    wh.codigo,
                    str(output_dir / f"{wh.codigo}.csv"),
                    filters=filters,
                )
                exported += 1
            except Exception as exc:  # pragma: no cover - user feedback path
                QMessageBox.warning(
                    self,
                    "Erro na exportação",
                    f"Falha ao exportar {wh.codigo}: {exc}",
                )
                return

        QMessageBox.information(
            self,
            "Exportação concluída",
            f"Exportação concluída para {exported} armazéns em {output_dir}.",
        )
        self.status_bar.showMessage(
            f"Exportação concluída ({exported} armazéns)",
            5000,
        )

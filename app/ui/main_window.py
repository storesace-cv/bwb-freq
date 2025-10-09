"""Main window for the requisitions UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.data.db import get_connection, init_db
from app.services.printer import export_context_json, export_csv_simple


@dataclass(slots=True)
class Warehouse:
    codigo: str
    nome: str


class MainWindow(QMainWindow):
    """Simple GUI for selecting warehouses and exporting requisition data."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Requisições Internas — MVP")
        init_db()

        self._warehouses: List[Warehouse] = []

        central = QWidget(self)
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
        layout.addWidget(self.list_widget)

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

        self.refresh_warehouses()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def refresh_warehouses(self) -> None:
        """Load the list of warehouses from the database."""

        self._warehouses = self._fetch_warehouses()
        self.list_widget.clear()
        for wh in self._warehouses:
            item = QListWidgetItem(f"{wh.codigo} — {wh.nome}")
            item.setData(Qt.UserRole, wh)
            self.list_widget.addItem(item)
        self.status_bar.showMessage(f"Armazéns disponíveis: {len(self._warehouses)}", 5000)

    def _fetch_warehouses(self) -> List[Warehouse]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT Codigo, Nome FROM Wharehouses ORDER BY Codigo"
            ).fetchall()
        return [Warehouse(codigo=row["Codigo"], nome=row["Nome"]) for row in rows]

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
        for wh in warehouses:
            try:
                export_context_json(wh.codigo, str(output_dir / f"{wh.codigo}.json"))
                export_csv_simple(wh.codigo, str(output_dir / f"{wh.codigo}.csv"))
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

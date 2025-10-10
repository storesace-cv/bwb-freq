"""Main window for the requisitions UI built with wxPython."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable

import wx

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
from app.ui.assets import APP_ICON, BACKGROUND_IMAGE
from app.ui.background_utils import BackgroundLayer
from app.utils.barcodes import classify_gs1_barcode


@dataclass(frozen=True)
class TableDisplayConfig:
    """Immutable configuration describing how to render a database table."""

    title: str
    columns: tuple[str, ...]
    query: str
    table_kind: str


HOME_TABLE_ID = "home_barcodes"


TABLE_CONFIGS: dict[str, TableDisplayConfig] = {
    HOME_TABLE_ID: TableDisplayConfig(
        title="Artigos | Códigos de Barras",
        columns=(
            "ArticleFoId",
            "ArticleName",
            "Barcode",
            "UnidadeName",
            "Familia",
            "SubFamilia",
            "Tipo de Código de Barras",
        ),
        query=(
            "SELECT "
            "    ab.ArticleFoId, "
            "    ab.ArticleName, "
            "    ab.Barcode, "
            "    ab.UnidadeName, "
            "    na.Familia, "
            "    na.SubFamilia "
            "FROM ArticleBarcodes AS ab "
            "LEFT JOIN NetboArticles AS na ON na.Codigo = ab.ArticleFoId "
            "WHERE ab.ArticleFoId NOT IN ("
            "    SELECT DISTINCT ft.Componente "
            "    FROM FichasTecnicas AS ft "
            "    JOIN NetboArticles AS generic ON generic.Codigo = ft.ProdVendaGenerico "
            "    WHERE IFNULL(generic.Generico, 0) = 1"
            ") "
            "ORDER BY "
            "    na.Familia COLLATE NOCASE, "
            "    na.SubFamilia COLLATE NOCASE, "
            "    ab.ArticleName COLLATE NOCASE"
        ),
        table_kind="barcodes",
    ),
    "netbo": TableDisplayConfig(
        title="Artigos",
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
        title="Departamentos",
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
        title="Artigos | Códigos de Barras",
        columns=(
            "ArticleFoId",
            "ArticleName",
            "Barcode",
            "UnidadeName",
            "Tipo de Código de Barras",
        ),
        query=(
            "SELECT ArticleFoId, ArticleName, Barcode, UnidadeName FROM ArticleBarcodes"
        ),
        table_kind="barcodes",
    ),
    "fichas_tecnicas": TableDisplayConfig(
        title="Artigos | Fichas Técnicas",
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


class MainWindow(wx.Frame):
    """Main application window using wxPython widgets."""

    def __init__(self) -> None:
        style = wx.DEFAULT_FRAME_STYLE
        super().__init__(None, title="Requisições Internas — MVP", size=(1024, 768), style=style)

        if APP_ICON.exists():
            try:
                self.SetIcon(wx.Icon(str(APP_ICON)))
            except Exception:  # pragma: no cover - icon issues
                pass

        init_db()

        self._background_layer = BackgroundLayer(self, BACKGROUND_IMAGE, "main-background")
        self._current_table_id: str | None = None
        self._barcode_column_index: int | None = None
        self._row_metadata: dict[int, dict[str, str]] = {}
        self._barcode_bitmap_cache: dict[str, wx.Bitmap] = {}
        self._open_barcode_dialogs: set[wx.Dialog] = set()

        self._build_ui()
        self._configure_menu()
        self._show_table(HOME_TABLE_ID)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        panel.SetName("central-panel")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(main_sizer)

        header = wx.Panel(panel)
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header.SetSizer(header_sizer)
        header.SetBackgroundColour(wx.Colour(240, 236, 229))

        title = wx.StaticText(header, label="Requisições Internas")
        title.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_SEMIBOLD))
        header_sizer.Add(title, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)

        close_button = wx.Button(header, label="Sair")
        close_button.Bind(wx.EVT_BUTTON, lambda _evt: self.Close())
        header_sizer.Add(close_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)

        main_sizer.Add(header, 0, wx.EXPAND)

        hint_panel = wx.Panel(panel)
        hint_sizer = wx.BoxSizer(wx.VERTICAL)
        hint_panel.SetSizer(hint_sizer)

        self.workspace_hint_default_text = "Selecione uma tabela em Menu ▸ Tabelas para visualizar os dados."
        self.workspace_hint = wx.StaticText(hint_panel, label=self.workspace_hint_default_text)
        self.workspace_hint.Wrap(760)
        hint_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.workspace_hint.SetFont(hint_font)
        hint_sizer.Add(self.workspace_hint, 0, wx.ALIGN_CENTER | wx.ALL, 20)

        main_sizer.Add(hint_panel, 0, wx.EXPAND)

        table_panel = wx.Panel(panel)
        table_panel.SetName("table-panel")
        table_panel.SetBackgroundColour(wx.Colour(250, 248, 244))
        table_sizer = wx.BoxSizer(wx.VERTICAL)
        table_panel.SetSizer(table_sizer)

        header_row = wx.BoxSizer(wx.HORIZONTAL)
        self.table_title = wx.StaticText(table_panel, label="")
        self.table_title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_SEMIBOLD))
        header_row.Add(self.table_title, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)

        self.close_table_button = wx.Button(table_panel, label="Fechar")
        self.close_table_button.Bind(wx.EVT_BUTTON, lambda _evt: self._close_table_view())
        header_row.Add(self.close_table_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)

        table_sizer.Add(header_row, 0, wx.EXPAND)

        self.table_widget = wx.ListCtrl(
            table_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SUNKEN,
        )
        self.table_widget.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        table_sizer.Add(self.table_widget, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        main_sizer.Add(table_panel, 1, wx.EXPAND | wx.ALL, 16)

        self.table_container = table_panel
        self._toggle_table_visibility(False)

        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetStatusText("Pronto")

        panel.Layout()

    def _configure_menu(self) -> None:
        menu_bar = wx.MenuBar()

        main_menu = wx.Menu()

        base_dados_menu = wx.Menu()
        self._add_menu_item(
            base_dados_menu,
            "Atualizar Dados",
            handler=self._update_database_from_excels,
        )
        self._add_menu_item(
            base_dados_menu,
            "Importar Dados",
            handler=self._import_incoming_excels,
        )

        seguranca_menu = wx.Menu()
        seguranca_menu.Append(wx.ID_ANY, "Segurança")
        seguranca_menu.Append(wx.ID_ANY, "Reposição")
        base_dados_menu.AppendSubMenu(seguranca_menu, "Segurança")

        main_menu.AppendSubMenu(base_dados_menu, "Base de Dados")

        tabelas_menu = wx.Menu()
        self._add_menu_item(tabelas_menu, "Artigos", handler=lambda: self._show_table("netbo"))
        self._add_menu_item(
            tabelas_menu,
            "Departamentos",
            handler=lambda: self._show_table("wharehouses"),
        )
        self._add_menu_item(
            tabelas_menu,
            "Artigos | Códigos de Barras",
            handler=lambda: self._show_table("barcodes"),
        )
        self._add_menu_item(
            tabelas_menu,
            "Artigos | Fichas Técnicas",
            handler=lambda: self._show_table("fichas_tecnicas"),
        )
        main_menu.AppendSubMenu(tabelas_menu, "Tabelas")

        utilitarios_menu = wx.Menu()
        gestao_documentos_menu = wx.Menu()
        gestao_documentos_menu.Append(wx.ID_ANY, "Editor de Documentos")
        gestao_documentos_menu.Append(wx.ID_ANY, "Modelos Activos")
        gestao_documentos_menu.Append(wx.ID_ANY, "Actualizar Documentos")
        utilitarios_menu.AppendSubMenu(gestao_documentos_menu, "Gestão de Documentos")
        utilitarios_menu.Append(wx.ID_ANY, "Configurações")
        main_menu.AppendSubMenu(utilitarios_menu, "Utilitários")

        parametrizacoes_menu = wx.Menu()
        integracao_menu = wx.Menu()
        integracao_menu.Append(wx.ID_ANY, "NETbo (Excel)")
        integracao_menu.Append(wx.ID_ANY, "NETbo (API)")
        integracao_menu.Append(wx.ID_ANY, "StoresAce (Excel)")
        parametrizacoes_menu.AppendSubMenu(integracao_menu, "Integração")
        parametrizacoes_menu.Append(wx.ID_ANY, "Moeda")
        main_menu.AppendSubMenu(parametrizacoes_menu, "Parametrizações")

        main_menu.AppendSeparator()
        self._add_menu_item(main_menu, "Sair", handler=self.Close)

        menu_bar.Append(main_menu, "Menu")
        self.SetMenuBar(menu_bar)

    def _add_menu_item(self, menu: wx.Menu, label: str, *, handler: Callable[[], None]) -> None:
        item_id = wx.NewIdRef()
        menu.Append(item_id, label)

        def _callback(_event: wx.CommandEvent) -> None:
            handler()

        self.Bind(wx.EVT_MENU, _callback, id=item_id)

    # ------------------------------------------------------------------
    # Table handling
    # ------------------------------------------------------------------
    def _show_table(self, table_id: str) -> None:
        self._current_table_id = table_id

        config = TABLE_CONFIGS.get(table_id)
        if config is None:
            raise ValueError(f"Unknown table identifier: {table_id}")

        rows = self._fetch_rows(config.query)
        self._populate_table(
            config.columns,
            rows,
            table_kind=config.table_kind,
            title=config.title,
        )

    def _fetch_rows(self, query: str) -> list:
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def _populate_table(
        self,
        columns: tuple[str, ...],
        rows: list,
        *,
        table_kind: str,
        title: str,
    ) -> None:
        self.table_widget.ClearAll()
        self._row_metadata.clear()
        self._barcode_column_index = columns.index("Barcode") if "Barcode" in columns else None

        for index, column in enumerate(columns):
            self.table_widget.InsertColumn(index, column)

        for row_index, row in enumerate(rows):
            barcode_value = None
            if self._barcode_column_index is not None:
                barcode_value = self._get_row_value(row, "Barcode", self._barcode_column_index)

            values: list[str] = []
            for col_index, column in enumerate(columns):
                if table_kind == "barcodes" and column == "Tipo de Código de Barras":
                    barcode_type = self._infer_barcode_type(barcode_value)
                    values.append(barcode_type or "-N/A-")
                    continue

                value = self._get_row_value(row, column, col_index)
                text = "" if value is None else str(value)
                values.append(text)

            item_index = self.table_widget.InsertItem(row_index, values[0]) if values else -1
            if item_index == -1:
                continue
            for col_index in range(1, len(values)):
                self.table_widget.SetItem(item_index, col_index, values[col_index])

            if barcode_value:
                self._row_metadata[item_index] = {"barcode": str(barcode_value)}

        self._toggle_table_visibility(True)

        if rows:
            for col_index in range(len(columns)):
                self.table_widget.SetColumnWidth(col_index, wx.LIST_AUTOSIZE)
                width = self.table_widget.GetColumnWidth(col_index)
                if width <= 0:
                    self.table_widget.SetColumnWidth(col_index, 120)
            self.workspace_hint.SetLabel(self.workspace_hint_default_text)
            self.workspace_hint.Show(False)
            hint_text = "Dê um duplo clique numa linha com código de barras para visualizar a imagem."
            self.status_bar.SetStatusText(hint_text)
        else:
            self.workspace_hint.SetLabel("Não existem registos para mostrar.")
            self.workspace_hint.Show(True)
            self.status_bar.SetStatusText("Sem registos disponíveis.")
            for col_index in range(len(columns)):
                self.table_widget.SetColumnWidth(col_index, wx.LIST_AUTOSIZE_USEHEADER)

        self.table_title.SetLabel(title)
        self.table_widget.Refresh()

    def _toggle_table_visibility(self, show: bool) -> None:
        self.table_container.Show(show)
        self.close_table_button.Enable(show)
        self.table_widget.Enable(show)
        self.Layout()

    def _close_table_view(self) -> None:
        self.table_widget.ClearAll()
        self.table_widget.Refresh()
        self.workspace_hint.SetLabel(self.workspace_hint_default_text)
        self.workspace_hint.Show(True)
        self.status_bar.SetStatusText("Tabela fechada.")
        self._toggle_table_visibility(False)

    # ------------------------------------------------------------------
    # Barcode handling
    # ------------------------------------------------------------------
    def _on_item_activated(self, event: wx.ListEvent) -> None:
        metadata = self._row_metadata.get(event.GetIndex())
        if not metadata:
            wx.MessageBox(
                "Não existe um código de barras para apresentar nesta linha.",
                "Código de barras indisponível",
                parent=self,
            )
            return

        barcode_value = metadata.get("barcode")
        if barcode_value:
            self._show_barcode_preview(barcode_value)

    def _show_barcode_preview(self, barcode_value: str) -> None:
        bitmap = self._get_barcode_bitmap(barcode_value)
        if bitmap is None or not bitmap.IsOk():
            wx.MessageBox(
                "Não foi possível gerar a imagem do código de barras.",
                "Pré-visualização indisponível",
                parent=self,
                style=wx.ICON_WARNING,
            )
            return

        dialog = wx.Dialog(self, title=f"Código de Barras — {barcode_value}")
        sizer = wx.BoxSizer(wx.VERTICAL)
        dialog.SetSizer(sizer)

        image = bitmap
        if image.GetHeight() > 220:
            scaled = image.ConvertToImage().Scale(
                image.GetWidth(),
                220,
                wx.IMAGE_QUALITY_HIGH,
            )
            image = wx.Bitmap(scaled)

        preview = wx.StaticBitmap(dialog, bitmap=image)
        preview.SetToolTip(barcode_value)
        sizer.Add(preview, 1, wx.ALIGN_CENTER | wx.ALL, 16)

        sizer.Fit(dialog)
        dialog.Layout()
        dialog.CentreOnParent()
        dialog.Show()
        self._open_barcode_dialogs.add(dialog)

        def _cleanup(_event: wx.Event) -> None:
            self._open_barcode_dialogs.discard(dialog)

        dialog.Bind(wx.EVT_WINDOW_DESTROY, _cleanup)

    def _get_barcode_bitmap(self, barcode_value: str | None) -> wx.Bitmap | None:
        if not barcode_value:
            return None
        if barcode_value in self._barcode_bitmap_cache:
            return self._barcode_bitmap_cache[barcode_value]

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
            data = buffer.getvalue()
            stream = wx.MemoryInputStream(data, len(data))
            image = wx.Image(stream, wx.BITMAP_TYPE_PNG)
            if image.IsOk():
                bitmap = wx.Bitmap(image)
                self._barcode_bitmap_cache[barcode_value] = bitmap
                return bitmap
        except Exception:  # pragma: no cover - invalid barcodes or wx failures
            return None
        return None

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

    # ------------------------------------------------------------------
    # Imports and data refresh helpers
    # ------------------------------------------------------------------
    def _update_database_from_excels(self) -> None:
        imported, missing, errors = self._process_incoming_excels()
        self._notify_import_results(imported, missing, errors)

        if imported:
            self._refresh_active_table()

    def _import_incoming_excels(self) -> None:
        imported, missing, errors = self._process_incoming_excels()
        self._notify_import_results(imported, missing, errors)

    def _process_incoming_excels(self) -> tuple[list[str], list[str], list[str]]:
        incoming_dir = Path("imports/incoming")
        processed_dir = Path("imports/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)

        tasks = (
            ("netbo_articles.xlsx", import_netbo_articles, "NetboArticles"),
            ("Lojas e Armazens.xlsx", import_wharehouses, "Wharehouses"),
            ("article_barcodes.xlsx", import_article_barcodes, "ArticleBarcodes"),
            ("Fichas Tecnicas.xlsx", import_fichas_tecnicas, "FichasTecnicas"),
        )

        imported: list[str] = []
        missing: list[str] = []
        errors: list[str] = []

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
        return imported, missing, errors

    def _notify_import_results(
        self,
        imported: list[str],
        missing: list[str],
        errors: list[str],
    ) -> None:
        if errors:
            message = "Ocorreram erros ao importar:\n" + "\n".join(errors)
            if imported:
                message += "\n\nImportações concluídas:\n" + "\n".join(imported)
            if missing:
                message += "\n\nFicheiros em falta:\n" + "\n".join(missing)
            wx.MessageBox(message, "Importação com erros", parent=self, style=wx.ICON_ERROR)
            return

        if not imported:
            if missing:
                message = (
                    "Não foram encontrados ficheiros para importar.\n\n"
                    "Esperados:\n" + "\n".join(missing)
                )
            else:
                message = "Não existem ficheiros para importar em imports/incoming."
            wx.MessageBox(message, "Sem dados", parent=self)
            return

        message_lines = ["Importação concluída com sucesso:"] + imported
        if missing:
            message_lines.append("\nFicheiros em falta:")
            message_lines.extend(missing)
        wx.MessageBox("\n".join(message_lines), "Importação concluída", parent=self)

    def _refresh_active_table(self) -> None:
        if not self._current_table_id:
            return
        try:
            self._show_table(self._current_table_id)
        except Exception:
            pass


__all__ = ["MainWindow", "TABLE_CONFIGS", "HOME_TABLE_ID"]

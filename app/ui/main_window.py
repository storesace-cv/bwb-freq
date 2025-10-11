"""Main window for the requisitions UI built with tkinter."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont

from PIL import Image, ImageTk

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


class MainWindow:
    """Main application window using tkinter widgets."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Requisições Internas — MVP")
        self.root.geometry("1024x768")
        self.root.minsize(960, 640)

        init_db()

        self._current_table_id: str | None = None
        self._barcode_column_index: int | None = None
        self._row_metadata: dict[str, dict[str, str]] = {}
        self._barcode_image_cache: dict[str, Image.Image] = {}
        self._open_barcode_dialogs: set[tk.Toplevel] = set()

        self._table_pack_options: dict[str, object]

        self._build_ui()
        self._configure_menu()
        self._show_table(HOME_TABLE_ID)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill="both", expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x")

        self.menu_button = ttk.Menubutton(header_frame, text="Menu")
        self.menu_button.pack(side="left", padx=12, pady=12)

        # tkinter only recognises "normal" and "bold" weight values, so use the
        # supported option here to avoid runtime errors on macOS/Linux.
        title_font = tkfont.Font(size=18, weight="bold")
        title_label = ttk.Label(header_frame, text="Requisições Internas", font=title_font)
        title_label.pack(side="left", padx=12, pady=12)

        self.workspace_hint_default_text = (
            "Selecione uma tabela em Menu ▸ Tabelas para visualizar os dados."
        )
        self.workspace_hint_var = tk.StringVar(value=self.workspace_hint_default_text)
        self.workspace_hint_frame = ttk.Frame(main_frame)
        self.workspace_hint_frame.pack(fill="x")
        hint_font = tkfont.Font(size=14)
        hint_label = ttk.Label(
            self.workspace_hint_frame,
            textvariable=self.workspace_hint_var,
            wraplength=760,
            font=hint_font,
            justify="center",
        )
        hint_label.pack(padx=20, pady=20)

        self.table_container = ttk.Frame(main_frame)
        self._table_pack_options = {"fill": "both", "expand": True, "pady": 16}
        self.table_container.pack(**self._table_pack_options)

        header_row = ttk.Frame(self.table_container)
        header_row.pack(fill="x")

        table_title_font = tkfont.Font(size=16, weight="bold")
        self.table_title_var = tk.StringVar(value="")
        table_title_label = ttk.Label(
            header_row, textvariable=self.table_title_var, font=table_title_font
        )
        table_title_label.pack(side="left", padx=8, pady=8)

        table_frame = ttk.Frame(self.table_container)
        table_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns: tuple[str, ...] = ()
        self.table_widget = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.table_widget.pack(side="left", fill="both", expand=True)
        self.table_widget.bind("<Double-1>", self._on_item_activated)

        scrollbar_y = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table_widget.yview
        )
        scrollbar_y.pack(side="right", fill="y")
        self.table_widget.configure(yscrollcommand=scrollbar_y.set)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Pronto")
        self.status_bar = ttk.Label(
            status_frame, textvariable=self.status_var, anchor="w", padding=(8, 4)
        )
        self.status_bar.pack(fill="x")

        self._toggle_table_visibility(False)

    def _configure_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        main_menu = tk.Menu(menu_bar, tearoff=False)

        base_dados_menu = tk.Menu(main_menu, tearoff=False)
        base_dados_menu.add_command(
            label="Atualizar Dados", command=self._update_database_from_excels
        )
        base_dados_menu.add_command(
            label="Importar Dados", command=self._import_incoming_excels
        )

        seguranca_menu = tk.Menu(base_dados_menu, tearoff=False)
        seguranca_menu.add_command(label="Segurança")
        seguranca_menu.add_command(label="Reposição")
        base_dados_menu.add_cascade(label="Segurança", menu=seguranca_menu)

        main_menu.add_cascade(label="Base de Dados", menu=base_dados_menu)

        tabelas_menu = tk.Menu(main_menu, tearoff=False)
        tabelas_menu.add_command(label="Artigos", command=lambda: self._show_table("netbo"))
        tabelas_menu.add_command(
            label="Departamentos", command=lambda: self._show_table("wharehouses")
        )
        tabelas_menu.add_command(
            label="Artigos | Códigos de Barras",
            command=lambda: self._show_table("barcodes"),
        )
        tabelas_menu.add_command(
            label="Artigos | Fichas Técnicas",
            command=lambda: self._show_table("fichas_tecnicas"),
        )
        main_menu.add_cascade(label="Tabelas", menu=tabelas_menu)

        utilitarios_menu = tk.Menu(main_menu, tearoff=False)
        gestao_documentos_menu = tk.Menu(utilitarios_menu, tearoff=False)
        gestao_documentos_menu.add_command(label="Editor de Documentos")
        gestao_documentos_menu.add_command(label="Modelos Activos")
        gestao_documentos_menu.add_command(label="Actualizar Documentos")
        utilitarios_menu.add_cascade(label="Gestão de Documentos", menu=gestao_documentos_menu)
        utilitarios_menu.add_command(label="Configurações")
        main_menu.add_cascade(label="Utilitários", menu=utilitarios_menu)

        parametrizacoes_menu = tk.Menu(main_menu, tearoff=False)
        integracao_menu = tk.Menu(parametrizacoes_menu, tearoff=False)
        integracao_menu.add_command(label="NETbo (Excel)")
        integracao_menu.add_command(label="NETbo (API)")
        integracao_menu.add_command(label="StoresAce (Excel)")
        parametrizacoes_menu.add_cascade(label="Integração", menu=integracao_menu)
        parametrizacoes_menu.add_command(label="Moeda")
        main_menu.add_cascade(label="Parametrizações", menu=parametrizacoes_menu)

        main_menu.add_separator()
        main_menu.add_command(label="Sair", command=self.root.destroy)

        menu_bar.add_cascade(label="Menu", menu=main_menu)
        if hasattr(self, "menu_button"):
            self.menu_button["menu"] = main_menu

        self.root.config(menu=menu_bar)

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
        for item in self.table_widget.get_children():
            self.table_widget.delete(item)

        self.table_widget.configure(columns=columns)
        self._row_metadata.clear()
        self._barcode_column_index = columns.index("Barcode") if "Barcode" in columns else None

        for column in columns:
            self.table_widget.heading(column, text=column, anchor="w")
            self.table_widget.column(column, anchor="w", width=150, stretch=True)

        for row in rows:
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

            item_id = self.table_widget.insert("", "end", values=values)
            if barcode_value:
                self._row_metadata[item_id] = {"barcode": str(barcode_value)}

        self._toggle_table_visibility(True)

        if rows:
            self._set_workspace_hint(self.workspace_hint_default_text, visible=False)
            hint_text = (
                "Dê um duplo clique numa linha com código de barras para visualizar a imagem."
            )
            self.status_var.set(hint_text)
            self._auto_size_columns(columns, rows)
        else:
            self._set_workspace_hint("Não existem registos para mostrar.", visible=True)
            self.status_var.set("Sem registos disponíveis.")

        self.table_title_var.set(title)

    def _toggle_table_visibility(self, show: bool) -> None:
        if show:
            if not self.table_container.winfo_manager():
                self.table_container.pack(**self._table_pack_options)
        else:
            if self.table_container.winfo_manager():
                self.table_container.pack_forget()

    def _set_workspace_hint(self, text: str, *, visible: bool) -> None:
        self.workspace_hint_var.set(text)
        if visible:
            if not self.workspace_hint_frame.winfo_manager():
                self.workspace_hint_frame.pack(fill="x")
        else:
            if self.workspace_hint_frame.winfo_manager():
                self.workspace_hint_frame.pack_forget()

    def _auto_size_columns(self, columns: tuple[str, ...], _rows: list) -> None:
        style = ttk.Style(self.table_widget)
        font_name = style.lookup("Treeview", "font")
        if not font_name:
            font = tkfont.nametofont("TkDefaultFont")
        else:
            try:
                font = tkfont.nametofont(font_name)
            except tk.TclError:
                font = tkfont.Font(name=font_name, exists=True)
        for column in columns:
            max_width = font.measure(column) + 24
            for item_id in self.table_widget.get_children():
                text = self.table_widget.set(item_id, column)
                max_width = max(max_width, font.measure(text) + 24)
            self.table_widget.column(column, width=max_width)

    def _close_table_view(self) -> None:
        for item in self.table_widget.get_children():
            self.table_widget.delete(item)
        self._set_workspace_hint(self.workspace_hint_default_text, visible=True)
        self.status_var.set("Tabela fechada.")
        self._toggle_table_visibility(False)

    # ------------------------------------------------------------------
    # Barcode handling
    # ------------------------------------------------------------------
    def _on_item_activated(self, _event: tk.Event) -> None:
        selection = self.table_widget.selection()
        if not selection:
            return
        item_id = selection[0]
        metadata = self._row_metadata.get(item_id)
        if not metadata:
            messagebox.showinfo(
                "Código de barras indisponível",
                "Não existe um código de barras para apresentar nesta linha.",
                parent=self.root,
            )
            return

        barcode_value = metadata.get("barcode")
        if barcode_value:
            self._show_barcode_preview(barcode_value)

    def _show_barcode_preview(self, barcode_value: str) -> None:
        image = self._get_barcode_image(barcode_value)
        if image is None:
            messagebox.showwarning(
                "Pré-visualização indisponível",
                "Não foi possível gerar a imagem do código de barras.",
                parent=self.root,
            )
            return

        preview_image = image
        if preview_image.height > 220:
            ratio = 220 / preview_image.height
            preview_image = preview_image.resize(
                (int(preview_image.width * ratio), 220), Image.LANCZOS
            )

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Código de Barras — {barcode_value}")
        dialog.transient(self.root)
        dialog.grab_set()

        photo = ImageTk.PhotoImage(preview_image)
        label = ttk.Label(dialog, image=photo)
        label.image = photo  # Prevent garbage collection.
        label.pack(padx=16, pady=16)

        self._open_barcode_dialogs.add(dialog)

        def _cleanup(_event: tk.Event) -> None:
            self._open_barcode_dialogs.discard(dialog)

        dialog.bind("<Destroy>", _cleanup)
        dialog.focus_set()

    def _get_barcode_image(self, barcode_value: str | None) -> Image.Image | None:
        if not barcode_value:
            return None
        if barcode_value in self._barcode_image_cache:
            return self._barcode_image_cache[barcode_value]

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
            buffer.seek(0)
            image = Image.open(buffer)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA")
            self._barcode_image_cache[barcode_value] = image
            return image
        except Exception:  # pragma: no cover - invalid barcodes or barcode failures
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
            messagebox.showerror(
                "Importação com erros",
                message,
                parent=self.root,
            )
            return

        if not imported:
            if missing:
                message = (
                    "Não foram encontrados ficheiros para importar.\n\n"
                    "Esperados:\n" + "\n".join(missing)
                )
            else:
                message = "Não existem ficheiros para importar em imports/incoming."
            messagebox.showinfo("Sem dados", message, parent=self.root)
            return

        message_lines = ["Importação concluída com sucesso:"] + imported
        if missing:
            message_lines.append("\nFicheiros em falta:")
            message_lines.extend(missing)
        messagebox.showinfo(
            "Importação concluída",
            "\n".join(message_lines),
            parent=self.root,
        )

    def _refresh_active_table(self) -> None:
        if not self._current_table_id:
            return
        try:
            self._show_table(self._current_table_id)
        except Exception:
            pass

    def center_on_screen(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")


__all__ = ["MainWindow", "TABLE_CONFIGS", "HOME_TABLE_ID"]

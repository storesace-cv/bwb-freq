from __future__ import annotations

from pathlib import Path

import pandas as pd


def _write_excel(path: Path, rows: list[dict]) -> Path:
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
    return path


def _load_basic_data(importer, dataset_paths):
    tmp_dir = Path(dataset_paths.articles).parent
    articles_path = _write_excel(
        tmp_dir / "sample_articles.xlsx",
        [
            {
                "Código": "A001",
                "Produto": "Água 0.5L",
                "Unidade": "UN",
                "Cod. Barras": "5601234567890",
                "Disp. Lojas": "10001, 10002",
            },
            {
                "Código": "A002",
                "Produto": "Café Torrado",
                "Unidade": "UN",
                "Cod. Barras": "",
                "Disp. Lojas": "10001",
            },
            {
                "Código": "A003",
                "Produto": "Chá Verde",
                "Unidade": "UN",
                "Cod. Barras": "",
                "Disp. Lojas": "10002",
            },
        ],
    )
    warehouses_path = _write_excel(
        tmp_dir / "sample_warehouses.xlsx",
        [
            {
                "Tipo": "Armazém",
                "Nome (#Código)": "Armazém Central (#10001)",
                "NIF": "500000000",
                "Tipo FO": "Central",
                "Teclado": "Central",
                "E-Mail do Responsável": "central@example.com",
            },
            {
                "Tipo": "Loja",
                "Nome (#Código)": "Loja Norte (#10002)",
                "NIF": "500000001",
                "Tipo FO": "Retail",
                "Teclado": "Loja",
                "E-Mail do Responsável": "norte@example.com",
            },
        ],
    )
    barcodes_path = _write_excel(
        tmp_dir / "sample_barcodes.xlsx",
        [
            {
                "article_fo_id": "A002",
                "article_name": "Café Torrado",
                "barcode": "ABC12345",
                "unit_id": "UN",
                "unidade_name": "UN",
                "price": 1.5,
                "store_names": "#10001; Loja Norte",
                "brand_names": "",
                "zone_names": "Bebidas",
            }
        ],
    )

    importer.import_wharehouses(str(warehouses_path))
    importer.import_netbo_articles(str(articles_path))
    importer.import_article_barcodes(str(barcodes_path))
    importer.build_warehouse_articles_from_disp()


def test_build_print_context_text_filter(app_services, dataset_paths):
    importer = app_services.importer
    printer = app_services.printer
    ArticleFilter = printer.ArticleFilter

    _load_basic_data(importer, dataset_paths)

    context = printer.build_print_context("10001")
    assert {a["Codigo"] for a in context["artigos"]} == {"A001", "A002"}

    filtered = printer.build_print_context(
        "10001",
        filters=ArticleFilter(text="café"),
    )
    assert [a["Codigo"] for a in filtered["artigos"]] == ["A002"]
    assert filtered["total_artigos"] == 1
    assert filtered["sem_barcode"] == 0


def test_build_print_context_only_missing_barcode(app_services, dataset_paths):
    importer = app_services.importer
    printer = app_services.printer
    ArticleFilter = printer.ArticleFilter

    _load_basic_data(importer, dataset_paths)

    filtered = printer.build_print_context(
        "10002",
        filters=ArticleFilter(only_missing_barcodes=True),
    )
    assert [a["Codigo"] for a in filtered["artigos"]] == ["A003"]
    assert filtered["total_artigos"] == 1
    assert filtered["sem_barcode"] == 1

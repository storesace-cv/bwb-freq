from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from app.services.importer import BARCODE_UNIQUE_INDEX_NAME


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_full_import_and_print_flow(app_services, dataset_paths, tmp_path):
    importer = app_services.importer
    printer = app_services.printer
    db = app_services.db

    articles = dataset_paths.articles
    warehouses = dataset_paths.warehouses
    barcodes = dataset_paths.barcodes
    fichas = dataset_paths.fichas_tecnicas

    importer.import_wharehouses(str(warehouses))
    importer.import_netbo_articles(str(articles))
    importer.import_article_barcodes(str(barcodes))
    importer.import_fichas_tecnicas(str(fichas))
    importer.build_warehouse_articles_from_disp()

    with db.get_connection() as conn:
        pairs = conn.execute(
            "SELECT WarehouseCodigo, ArticleCodigo FROM WarehouseArticles ORDER BY WarehouseCodigo, ArticleCodigo"
        ).fetchall()
    assert [(r["WarehouseCodigo"], r["ArticleCodigo"]) for r in pairs] == [
        ("10001", "A001"),
        ("10001", "A002"),
        ("10002", "A001"),
        ("10002", "A003"),
    ]

    out_json = tmp_path / "10001.json"
    printer.export_context_json("10001", str(out_json))
    data = json.loads(out_json.read_text(encoding="utf-8"))

    assert data["warehouse"]["Codigo"] == "10001"
    assert data["warehouse"]["Nome"].startswith("Armazém Central")
    assert data["total_artigos"] == 2
    assert data["sem_barcode"] == 0

    artigos = {item["Codigo"]: item for item in data["artigos"]}
    assert set(artigos) == {"A001", "A002"}
    assert artigos["A001"]["barcode_value"] == "5601234567890"
    assert artigos["A001"]["barcode_type"] == "EAN13"
    assert artigos["A002"]["barcode_value"] == "ABC12345"
    assert artigos["A002"]["barcode_type"] == "Code128"

    out_csv = tmp_path / "10001.csv"
    printer.export_csv_simple("10001", str(out_csv))
    csv_rows = _read_csv(out_csv)
    assert len(csv_rows) == 2
    assert {row["Codigo"] for row in csv_rows} == {"A001", "A002"}

    out_json_10002 = tmp_path / "10002.json"
    printer.export_context_json("10002", str(out_json_10002))
    data_10002 = json.loads(out_json_10002.read_text(encoding="utf-8"))
    assert data_10002["total_artigos"] == 2
    assert data_10002["sem_barcode"] == 1
    artigos_10002 = {item["Codigo"]: item for item in data_10002["artigos"]}
    assert artigos_10002["A003"]["barcode_value"] is None

    with db.get_connection() as conn:
        fichas_rows = conn.execute(
            "SELECT ProdVendaGenerico, Componente, Quantidade, Unidade FROM FichasTecnicas ORDER BY Componente"
        ).fetchall()
    assert [
        (row["ProdVendaGenerico"], row["Componente"], row["Quantidade"], row["Unidade"])
        for row in fichas_rows
    ] == [
        ("A001", "A002", 2.0, "UN"),
        ("A001", "A003", 1.0, "UN"),
    ]


def test_import_wharehouses_requires_codigo(app_services, dataset_paths):
    importer = app_services.importer
    invalid = dataset_paths.invalid_warehouses
    with pytest.raises(ValueError):
        importer.import_wharehouses(str(invalid))


def test_import_article_barcodes_is_idempotent(app_services, dataset_paths):
    importer = app_services.importer
    db = app_services.db

    importer.import_article_barcodes(str(dataset_paths.barcodes))
    importer.import_article_barcodes(str(dataset_paths.barcodes))

    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT ArticleFoId, Barcode FROM ArticleBarcodes ORDER BY ArticleFoId"
        ).fetchall()
    assert [(row["ArticleFoId"], row["Barcode"]) for row in rows] == [("A002", "ABC12345")]


def test_remove_duplicate_article_barcodes(app_services, dataset_paths):
    importer = app_services.importer
    db = app_services.db

    importer.import_article_barcodes(str(dataset_paths.barcodes))

    with db.get_connection() as conn:
        conn.execute(f"DROP INDEX IF EXISTS {BARCODE_UNIQUE_INDEX_NAME}")
        conn.execute(
            "INSERT INTO ArticleBarcodes (ArticleFoId, ArticleName, Barcode, UnidadeName) "
            "VALUES (?, ?, ?, ?)",
            ("A002", "Café Torrado", "ABC12345", "UN"),
        )
        conn.execute(
            "INSERT INTO ArticleBarcodes (ArticleFoId, ArticleName, Barcode, UnidadeName) "
            "VALUES (?, ?, ?, ?)",
            ("A002", "Café Torrado", "ABC12345", "UN"),
        )
        conn.commit()

    assert importer.count_duplicate_article_barcodes() == 2
    removed = importer.remove_duplicate_article_barcodes()
    assert removed == 2
    assert importer.count_duplicate_article_barcodes() == 0

    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT ArticleFoId, Barcode FROM ArticleBarcodes ORDER BY ArticleFoId"
        ).fetchall()
    assert [(row["ArticleFoId"], row["Barcode"]) for row in rows] == [("A002", "ABC12345")]

    with pytest.raises(sqlite3.IntegrityError):
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO ArticleBarcodes (ArticleFoId, ArticleName, Barcode, UnidadeName) "
                "VALUES (?, ?, ?, ?)",
                ("A002", "Café Torrado", "ABC12345", "UN"),
            )

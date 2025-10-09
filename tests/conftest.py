from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_modules():
    import app.data.db as db
    import app.services.barcode_resolver as barcode_resolver
    import app.services.importer as importer
    import app.services.printer as printer

    importlib.reload(db)
    importlib.reload(barcode_resolver)
    importlib.reload(importer)
    importlib.reload(printer)
    return SimpleNamespace(
        db=db,
        barcode_resolver=barcode_resolver,
        importer=importer,
        printer=printer,
    )


def _write_excel(path: Path, data: list[dict]):
    df = pd.DataFrame(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)


def _ensure_example(
    tmp_dir: Path,
    examples_dir: Path,
    filename: str,
    *,
    fallback: list[dict],
):
    src = examples_dir / filename
    dest = tmp_dir / filename
    if os.environ.get("USE_REAL_IMPORT_EXAMPLES") and src.exists():
        shutil.copy(src, dest)
    else:
        _write_excel(dest, fallback)
    return dest


@pytest.fixture
def dataset_paths(tmp_path) -> SimpleNamespace:
    examples_dir = PROJECT_ROOT / "imports" / "examples"
    tmp_dir = tmp_path / "datasets"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    articles = _ensure_example(
        tmp_dir,
        examples_dir,
        "netbo_articles.xlsx",
        fallback=[
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

    warehouses = _ensure_example(
        tmp_dir,
        examples_dir,
        "Lojas e Armazens.xlsx",
        fallback=[
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

    barcodes = _ensure_example(
        tmp_dir,
        examples_dir,
        "article_barcodes.xlsx",
        fallback=[
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

    invalid_warehouses = _ensure_example(
        tmp_dir,
        examples_dir,
        "Lojas e Armazens sem codigo.xlsx",
        fallback=[
            {
                "Tipo": "Loja",
                "Nome (#Código)": "Loja Sem Codigo",
                "NIF": "500000002",
                "Tipo FO": "Retail",
                "Teclado": "Loja",
                "E-Mail do Responsável": "semcodigo@example.com",
            }
        ],
    )

    return SimpleNamespace(
        articles=articles,
        warehouses=warehouses,
        barcodes=barcodes,
        invalid_warehouses=invalid_warehouses,
    )


@pytest.fixture
def app_services(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    modules = _reload_modules()
    modules.db.init_db()
    return modules

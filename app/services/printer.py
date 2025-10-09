from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping

from app.data.db import get_connection
from app.services.barcode_resolver import build_barcode_lookup, resolve_barcode


@dataclass(slots=True)
class ArticleFilter:
    """Filter configuration used to narrow down the article list."""

    text: str = ""
    only_missing_barcodes: bool = False

    def normalised_text(self) -> str:
        return self.text.casefold().strip()


def _load_barcode_lookup(conn) -> Dict[str, List[dict]]:
    rows = conn.execute(
        "SELECT ArticleFoId, Barcode, StoreNames FROM ArticleBarcodes"
    ).fetchall()
    return build_barcode_lookup(dict(r) for r in rows)


def _gather_for_warehouse(warehouse_codigo: str):
    with get_connection() as conn:
        wh = conn.execute(
            "SELECT * FROM Wharehouses WHERE Codigo = ?", (warehouse_codigo,)
        ).fetchone()
        if not wh:
            raise ValueError(f"Warehouse '{warehouse_codigo}' não existe")
        barcodes = _load_barcode_lookup(conn)
        q = conn.execute(
            """
          SELECT a.Codigo, a.Produto, a.Unidade, a.CodBarras
          FROM WarehouseArticles wa
          JOIN NetboArticles a ON a.Codigo = wa.ArticleCodigo
          WHERE wa.WarehouseCodigo = ?
          ORDER BY a.Produto
        """,
            (warehouse_codigo,),
        )
        artigos = []
        for r in q:
            val, btype = resolve_barcode(
                r["Codigo"],
                r["CodBarras"],
                barcodes,
                warehouse_codigo,
            )
            artigos.append(
                {
                    "Codigo": r["Codigo"],
                    "Produto": r["Produto"],
                    "Unidade": r["Unidade"],
                    "Quantidade": 0,
                    "barcode_value": val,
                    "barcode_type": btype,
                }
            )
        return dict(wh), artigos


def _filter_articles(
    artigos: Iterable[MutableMapping[str, object]],
    article_filter: ArticleFilter | None,
) -> List[dict]:
    if article_filter is None:
        return [dict(a) for a in artigos]

    text = article_filter.normalised_text()
    filtered: List[dict] = []
    for artigo in artigos:
        codigo = str(artigo.get("Codigo", ""))
        produto = str(artigo.get("Produto", ""))
        barcode_value = artigo.get("barcode_value")

        if text and text not in codigo.casefold() and text not in produto.casefold():
            continue
        if article_filter.only_missing_barcodes and barcode_value:
            continue
        filtered.append(dict(artigo))
    return filtered


def filter_articles(
    artigos: Iterable[MutableMapping[str, object]],
    article_filter: ArticleFilter | None = None,
) -> List[dict]:
    """Public helper to filter article rows according to ``ArticleFilter``."""

    return _filter_articles(artigos, article_filter)


def build_print_context(
    warehouse_codigo: str,
    *,
    filters: ArticleFilter | None = None,
) -> dict:
    """Build the JSON context used by ReportBro and CSV exports."""

    wh, artigos = _gather_for_warehouse(warehouse_codigo)
    filtered_artigos = _filter_articles(artigos, filters)
    context = {
        "warehouse": {"Codigo": wh["Codigo"], "Nome": wh["Nome"]},
        "artigos": filtered_artigos,
        "sem_barcode": sum(1 for a in filtered_artigos if not a["barcode_value"]),
        "total_artigos": len(filtered_artigos),
    }
    return context


def export_context_json(
    warehouse_codigo: str,
    out_path: str,
    *,
    filters: ArticleFilter | None = None,
) -> None:
    ctx = build_print_context(warehouse_codigo, filters=filters)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)


def export_csv_simple(
    warehouse_codigo: str,
    out_csv: str,
    *,
    filters: ArticleFilter | None = None,
) -> None:
    artigos = build_print_context(warehouse_codigo, filters=filters)["artigos"]
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Codigo",
                "Produto",
                "Unidade",
                "Quantidade",
                "barcode_value",
                "barcode_type",
            ],
        )
        w.writeheader()
        for a in artigos:
            w.writerow(a)

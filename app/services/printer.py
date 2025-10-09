import csv, json
from pathlib import Path
from app.data.db import get_connection
from app.services.barcode_resolver import resolve_barcode

def _fetch_barcodes(conn):
    rows = conn.execute("SELECT ArticleFoId, Barcode, StoreNames FROM ArticleBarcodes").fetchall()
    return [dict(r) for r in rows]

def _gather_for_warehouse(warehouse_codigo: str):
    with get_connection() as conn:
        wh = conn.execute("SELECT * FROM Wharehouses WHERE Codigo = ?", (warehouse_codigo,)).fetchone()
        if not wh:
            raise ValueError(f"Warehouse '{warehouse_codigo}' não existe")
        barcodes = _fetch_barcodes(conn)
        q = conn.execute("""
          SELECT a.Codigo, a.Produto, a.Unidade, a.CodBarras
          FROM WarehouseArticles wa
          JOIN NetboArticles a ON a.Codigo = wa.ArticleCodigo
          WHERE wa.WarehouseCodigo = ?
          ORDER BY a.Produto
        """, (warehouse_codigo,))
        artigos = []
        for r in q:
            val, btype = resolve_barcode(r["Codigo"], r["CodBarras"], barcodes, warehouse_codigo)
            artigos.append({
                "Codigo": r["Codigo"],
                "Produto": r["Produto"],
                "Unidade": r["Unidade"],
                "Quantidade": 0,
                "barcode_value": val,
                "barcode_type": btype
            })
        return dict(wh), artigos

def export_context_json(warehouse_codigo: str, out_path: str):
    wh, artigos = _gather_for_warehouse(warehouse_codigo)
    ctx = {
        "warehouse": {"Codigo": wh["Codigo"], "Nome": wh["Nome"]},
        "artigos": artigos,
        "sem_barcode": sum(1 for a in artigos if not a["barcode_value"]),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)

def export_csv_simple(warehouse_codigo: str, out_csv: str):
    _, artigos = _gather_for_warehouse(warehouse_codigo)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Codigo","Produto","Unidade","Quantidade","barcode_value","barcode_type"])
        w.writeheader()
        for a in artigos:
            w.writerow(a)

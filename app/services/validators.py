from app.data.db import get_connection

def validate_integrity() -> dict:
    rep = {"errors": [], "warnings": [], "counts": {}}
    with get_connection() as conn:
        def count(t):
            return conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        rep["counts"] = {
            "NetboArticles": count("NetboArticles"),
            "Wharehouses": count("Wharehouses"),
            "ArticleBarcodes": count("ArticleBarcodes"),
            "WarehouseArticles": count("WarehouseArticles"),
        }
        # WarehouseArticles com warehouse desconhecido
        bad = conn.execute("""
            SELECT wa.WarehouseCodigo FROM WarehouseArticles wa
            LEFT JOIN Wharehouses w ON w.Codigo = wa.WarehouseCodigo
            WHERE w.Codigo IS NULL
        """).fetchall()
        if bad:
            rep["warnings"].append(f"Relações WA com warehouse desconhecido: {len(bad)}")
        # Barcodes órfãos
        orf = conn.execute("""
            SELECT COUNT(*) FROM ArticleBarcodes b
            LEFT JOIN NetboArticles n ON n.Codigo = b.ArticleFoId
            WHERE n.Codigo IS NULL
        """).fetchone()[0]
        if orf:
            rep["warnings"].append(f"ArticleBarcodes órfãos (ArticleFoId sem match): {orf}")
    return rep

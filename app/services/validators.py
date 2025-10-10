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
            "FichasTecnicas": count("FichasTecnicas"),
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

        fichas_missing_prod = conn.execute("""
            SELECT COUNT(*) FROM FichasTecnicas ft
            LEFT JOIN NetboArticles n ON n.Codigo = ft.ProdVendaGenerico
            WHERE n.Codigo IS NULL
        """).fetchone()[0]
        if fichas_missing_prod:
            rep["warnings"].append(
                f"FichasTecnicas órfãs (ProdVendaGenerico sem artigo): {fichas_missing_prod}"
            )

        fichas_missing_comp = conn.execute("""
            SELECT COUNT(*) FROM FichasTecnicas ft
            LEFT JOIN NetboArticles n ON n.Codigo = ft.Componente
            WHERE n.Codigo IS NULL
        """).fetchone()[0]
        if fichas_missing_comp:
            rep["warnings"].append(
                f"FichasTecnicas com componente desconhecido: {fichas_missing_comp}"
            )
    return rep

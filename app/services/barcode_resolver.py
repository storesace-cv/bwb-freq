def _is_ean13(s: str) -> bool:
    return s.isdigit() and len(s) == 13

def resolve_barcode(article_codigo, article_cod_barras, barcodes_rows, warehouse_codigo):
    # Prefer ArticleBarcodes matching ArticleFoId and StoreNames containing warehouse code (if provided)
    for row in barcodes_rows:
        if row.get("ArticleFoId") == article_codigo:
            stores = (row.get("StoreNames") or "").strip()
            if not stores or warehouse_codigo in stores:
                val = (row.get("Barcode") or "").strip()
                if val:
                    return val, ("EAN13" if _is_ean13(val) else "Code128")
    # Fallback to any ArticleBarcodes by ArticleFoId
    for row in barcodes_rows:
        if row.get("ArticleFoId") == article_codigo:
            val = (row.get("Barcode") or "").strip()
            if val:
                return val, ("EAN13" if _is_ean13(val) else "Code128")
    # Fallback to NetboArticles.CodBarras
    if article_cod_barras:
        val = article_cod_barras.strip()
        if val:
            return val, ("EAN13" if _is_ean13(val) else "Code128")
    return None, None

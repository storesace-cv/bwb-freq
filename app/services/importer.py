import re
import pandas as pd
from app.data.db import get_connection

def _norm_bool(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in {"1","true","yes","sim"}:
        return 1
    if s in {"0","false","no","não","nao"}:
        return 0
    try:
        return 1 if float(s) != 0 else 0
    except Exception:
        return None

def import_netbo_articles(xlsx_path: str) -> int:
    df = pd.read_excel(xlsx_path, dtype=str).fillna("")
    mapping = {
        "Código":"Codigo","Produto":"Produto","Família":"Familia","Sub Família":"SubFamilia",
        "Cod. Barras":"CodBarras","Afeta Stock":"AfetaStock","Menu":"Menu","Venda":"Venda",
        "Mercadoria":"Mercadoria","Produção":"Producao","Genérico":"Generico","Intermédio":"Intermedio",
        "Serviço":"Servico","Unidade":"Unidade","Un. Venda":"UnVenda","Un. Inventário":"UnInventario",
        "Un. Produção":"UnProducao","Cod. Auxiliar":"CodAuxiliar","Cod. Auxiliar 2":"CodAuxiliar2",
        "PCU":"Pcu","PCM":"Pcm","Descontinuado":"Descontinuado","Qtd. Negativas nas Compras":"QtdNegativasNasCompras",
        "Controla Números de Série":"ControlaNumerosDeSerie","Disp. Lojas":"DispLojas",
        "Peso Transporte":"PesoTransporte","Markup (%)":"Markup","Tipo de Produto (SAF-T - P,S,O,I,E)":"TipoDeProdutoSaftPsoie"
    }
    df = df.rename(columns={k:v for k,v in mapping.items() if k in df.columns})
    bool_cols = ["AfetaStock","Menu","Venda","Mercadoria","Producao","Generico","Intermedio","Servico",
                 "Descontinuado","QtdNegativasNasCompras","ControlaNumerosDeSerie"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].apply(_norm_bool)

    with get_connection() as conn:
        n = 0
        cols = list(df.columns)
        placeholders = ",".join([f":{c}" for c in cols])
        for _, r in df.iterrows():
            codigo = r.get("Codigo","").strip()
            if not codigo:
                continue
            conn.execute(f"INSERT OR REPLACE INTO NetboArticles ({','.join(cols)}) VALUES ({placeholders})", dict(r))
            n += 1
        conn.execute("INSERT INTO ImportsLog("When", File, Kind, Rows, Notes) VALUES(datetime('now'), ?, 'articles', ?, NULL)", (xlsx_path, n))
        conn.commit()
        return n

def import_wharehouses(xlsx_path: str) -> int:
    df = pd.read_excel(xlsx_path, dtype=str).fillna("")
    mapping = {"Tipo":"Tipo","Nome (#Código)":"Nome","NIF":"Nif","Tipo FO":"TipoFo","Teclado":"Teclado","E-Mail do Responsável":"EmailDoResponsavel"}
    df = df.rename(columns={k:v for k,v in mapping.items() if k in df.columns})
    rx = re.compile(r"\(#(?P<Codigo>[0-9]+)\)")
    codigos = []
    for _, r in df.iterrows():
        m = rx.search(r.get("Nome",""))
        codigos.append(m.group("Codigo") if m else "")
    df["Codigo"] = codigos

    with get_connection() as conn:
        n = 0
        cols = ["Codigo","Tipo","Nome","Nif","TipoFo","Teclado","EmailDoResponsavel"]
        placeholders = ",".join([f":{c}" for c in cols])
        for _, r in df.iterrows():
            if not r.get("Codigo","").strip():
                raise ValueError(f"Não foi possível extrair Codigo de Nome='{r.get('Nome','')}'")
            conn.execute(f"INSERT OR REPLACE INTO Wharehouses ({','.join(cols)}) VALUES ({placeholders})", {c:r.get(c,"") for c in cols})
            n += 1
        conn.execute("INSERT INTO ImportsLog("When", File, Kind, Rows, Notes) VALUES(datetime('now'), ?, 'warehouses', ?, NULL)", (xlsx_path, n))
        conn.commit()
        return n

def import_article_barcodes(xlsx_path: str) -> int:
    df = pd.read_excel(xlsx_path, dtype=str).fillna("")
    mapping = {
        "article_fo_id":"ArticleFoId","article_name":"ArticleName","barcode":"Barcode",
        "unit_id":"UnitId","unidade_name":"UnidadeName","price":"Price",
        "store_names":"StoreNames","brand_names":"BrandNames","zone_names":"ZoneNames"
    }
    df = df.rename(columns={k:v for k,v in mapping.items() if k in df.columns})

    with get_connection() as conn:
        n = 0
        cols = list(df.columns)
        placeholders = ",".join([f":{c}" for c in cols]).replace('"', '')  # ensure :col without quotes
        for _, r in df.iterrows():
            conn.execute(f"INSERT INTO ArticleBarcodes ({','.join(cols)}) VALUES ({placeholders})", dict(r))
            n += 1
        conn.execute("INSERT INTO ImportsLog("When", File, Kind, Rows, Notes) VALUES(datetime('now'), ?, 'barcodes', ?, NULL)", (xlsx_path, n))
        conn.commit()
        return n

def build_warehouse_articles_from_disp():
    with get_connection() as conn:
        rows = conn.execute("SELECT Codigo, DispLojas FROM NetboArticles WHERE IFNULL(DispLojas,'') <> ''").fetchall()
        pairs = set()
        for r in rows:
            art = r["Codigo"]
            disp = [x.strip() for x in str(r["DispLojas"]).split(",") if x.strip()]
            for code in disp:
                code = ''.join([c for c in code if c.isdigit()])
                if code:
                    pairs.add((code, art))
        for wh, art in pairs:
            conn.execute("INSERT OR IGNORE INTO WarehouseArticles (WarehouseCodigo, ArticleCodigo) VALUES (?, ?)", (wh, art))
        conn.commit()

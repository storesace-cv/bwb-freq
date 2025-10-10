import argparse, os, sys
from pathlib import Path
from app.data.db import init_db, get_connection
from app.services.importer import (
    import_netbo_articles,
    import_wharehouses,
    import_article_barcodes,
    import_fichas_tecnicas,
    build_warehouse_articles_from_disp,
)
from app.services.validators import validate_integrity
from app.services.printer import export_context_json, export_csv_simple

def cmd_import(args):
    init_db()
    if args.articles:
        n = import_netbo_articles(args.articles)
        print(f"[import] NetboArticles: {n} linhas")
    if args.warehouses:
        n = import_wharehouses(args.warehouses)
        print(f"[import] Wharehouses: {n} linhas")
    if args.barcodes:
        n = import_article_barcodes(args.barcodes)
        print(f"[import] ArticleBarcodes: {n} linhas")
    if args.fichas:
        n = import_fichas_tecnicas(args.fichas)
        print(f"[import] FichasTecnicas: {n} linhas")
    build_warehouse_articles_from_disp()
    print("[import] WarehouseArticles atualizado a partir de DispLojas")

def cmd_validate(_args):
    rep = validate_integrity()
    print("[validate] counts:", rep["counts"])
    for w in rep["warnings"]:
        print("[warn]", w)
    if rep["errors"]:
        for e in rep["errors"]:
            print("[error]", e)
        sys.exit(2)

def cmd_print(args):
    out = args.out or "out"
    Path(out).mkdir(parents=True, exist_ok=True)
    if args.warehouse:
        export_context_json(args.warehouse, os.path.join(out, f"{args.warehouse}.json"))
        export_csv_simple(args.warehouse, os.path.join(out, f"{args.warehouse}.csv"))
        print(f"[print] Exportados JSON+CSV para {args.warehouse}")
    elif args.all:
        with get_connection() as conn:
            rows = conn.execute("SELECT Codigo FROM Wharehouses ORDER BY Codigo").fetchall()
        for r in rows:
            code = r["Codigo"]
            export_context_json(code, os.path.join(out, f"{code}.json"))
            export_csv_simple(code, os.path.join(out, f"{code}.csv"))
            print(f"[print] {code} OK")
    else:
        print("Obrigatório --warehouse <Codigo> ou --all")
        sys.exit(2)

def main(argv=None):
    p = argparse.ArgumentParser(prog="requisicoes")
    sub = p.add_subparsers(dest="cmd")

    p_imp = sub.add_parser("import", help="Importar Excel para SQLite")
    p_imp.add_argument("--articles", help="caminho para netbo_articles.xlsx")
    p_imp.add_argument("--warehouses", help="caminho para Lojas e Armazens.xlsx")
    p_imp.add_argument("--barcodes", help="caminho para article_barcodes.xlsx")
    p_imp.add_argument("--fichas", help="caminho para Fichas Tecnicas.xlsx")
    p_imp.set_defaults(func=cmd_import)

    p_val = sub.add_parser("validate", help="Validar integridade de dados")
    p_val.set_defaults(func=cmd_validate)

    p_prn = sub.add_parser("print", help="Gerar outputs por armazém (JSON/CSV p/ ReportBro)")
    g = p_prn.add_mutually_exclusive_group(required=True)
    g.add_argument("--warehouse", type=str, help="Código do armazém")
    g.add_argument("--all", action="store_true", help="Todos os armazéns")
    p_prn.add_argument("--out", type=str, help="Diretório de saída (default: ./out)")
    p_prn.set_defaults(func=cmd_print)

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())

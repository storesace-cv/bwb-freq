PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS NetboArticles (
  Codigo TEXT PRIMARY KEY,
  Produto TEXT,
  Familia TEXT,
  SubFamilia TEXT,
  CodBarras TEXT,
  AfetaStock INTEGER,
  Menu INTEGER,
  Venda INTEGER,
  Mercadoria INTEGER,
  Producao INTEGER,
  Generico INTEGER,
  Intermedio INTEGER,
  Servico INTEGER,
  Unidade TEXT,
  UnVenda TEXT,
  UnInventario TEXT,
  UnProducao TEXT,
  CodAuxiliar TEXT,
  CodAuxiliar2 TEXT,
  Pcu REAL,
  Pcm REAL,
  Descontinuado INTEGER,
  QtdNegativasNasCompras INTEGER,
  ControlaNumerosDeSerie INTEGER,
  DispLojas TEXT,
  PesoTransporte REAL,
  Markup REAL,
  TipoDeProdutoSaftPsoie TEXT
);

CREATE TABLE IF NOT EXISTS Wharehouses (
  Codigo TEXT PRIMARY KEY,
  Tipo TEXT,
  Nome TEXT,
  Nif TEXT,
  TipoFo TEXT,
  Teclado TEXT,
  EmailDoResponsavel TEXT
);

CREATE TABLE IF NOT EXISTS ArticleBarcodes (
  Id INTEGER PRIMARY KEY AUTOINCREMENT,
  ArticleFoId TEXT,
  ArticleName TEXT,
  Barcode TEXT,
  UnitId TEXT,
  UnidadeName TEXT,
  Price REAL,
  StoreNames TEXT,
  BrandNames TEXT,
  ZoneNames TEXT,
  FOREIGN KEY (ArticleFoId) REFERENCES NetboArticles(Codigo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS FichasTecnicas (
  ProdVendaGenerico TEXT NOT NULL,
  Componente TEXT NOT NULL,
  Quantidade REAL,
  Unidade TEXT,
  NomeProdVendaGenerico TEXT,
  NomeComponente TEXT,
  PRIMARY KEY (ProdVendaGenerico, Componente),
  FOREIGN KEY (ProdVendaGenerico) REFERENCES NetboArticles(Codigo) ON DELETE CASCADE,
  FOREIGN KEY (Componente) REFERENCES NetboArticles(Codigo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS WarehouseArticles (
  WarehouseCodigo TEXT NOT NULL,
  ArticleCodigo TEXT NOT NULL,
  PRIMARY KEY (WarehouseCodigo, ArticleCodigo),
  FOREIGN KEY (WarehouseCodigo) REFERENCES Wharehouses(Codigo) ON DELETE CASCADE,
  FOREIGN KEY (ArticleCodigo) REFERENCES NetboArticles(Codigo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Requisitions (
  Id INTEGER PRIMARY KEY AUTOINCREMENT,
  WarehouseCodigo TEXT NOT NULL,
  CreatedAt TEXT NOT NULL DEFAULT (datetime('now')),
  Status TEXT DEFAULT 'draft',
  FOREIGN KEY (WarehouseCodigo) REFERENCES Wharehouses(Codigo) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS RequisitionLines (
  Id INTEGER PRIMARY KEY AUTOINCREMENT,
  RequisitionId INTEGER NOT NULL,
  ArticleCodigo TEXT NOT NULL,
  Produto TEXT,
  Quantidade REAL NOT NULL DEFAULT 0,
  Unidade TEXT,
  Barcode TEXT,
  FOREIGN KEY (RequisitionId) REFERENCES Requisitions(Id) ON DELETE CASCADE,
  FOREIGN KEY (ArticleCodigo) REFERENCES NetboArticles(Codigo) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Settings (
  Key TEXT PRIMARY KEY,
  Value TEXT
);

CREATE TABLE IF NOT EXISTS ImportsLog (
  Id INTEGER PRIMARY KEY AUTOINCREMENT,
  "When" TEXT,
  File TEXT,
  Kind TEXT,
  Rows INTEGER,
  Notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_articlebarcodes_foid ON ArticleBarcodes(ArticleFoId);
CREATE UNIQUE INDEX IF NOT EXISTS uq_article_barcodes_article_barcode ON ArticleBarcodes(ArticleFoId, Barcode);
CREATE INDEX IF NOT EXISTS idx_requisition_lines_req ON RequisitionLines(RequisitionId);

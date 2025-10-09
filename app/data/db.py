import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./databases/requisicoes.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

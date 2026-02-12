# db.py
import sqlite3
import os
import json

DEFAULT_DATA_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "AnnualInspectionSystem", "data")
CONFIG_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "AnnualInspectionSystem")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def _load_data_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            val = data.get("data_dir")
            if isinstance(val, str) and val.strip():
                return val
        except Exception:
            pass

    default_dir = os.environ.get("ANNUAL_INSPECTION_DATA_DIR", DEFAULT_DATA_DIR)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"data_dir": default_dir}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return default_dir

DATA_DIR = _load_data_dir()
DB_NAME = os.path.join(DATA_DIR, "inspection.db")

def get_data_dir():
    return DATA_DIR

def get_config_path():
    return CONFIG_PATH

def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                done_date TEXT,
                next_date TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                done_date TEXT,
                next_date TEXT,
                notes TEXT,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        #  PERFORMANCE INDEXES (paste here)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_companies_next ON companies(next_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_inspections_company_date ON inspections(company_id, done_date)"
        )

        cur = conn.execute("SELECT COUNT(*) FROM inspections")
        if cur.fetchone()[0] == 0:
            conn.execute("""
                INSERT INTO inspections (company_id, done_date, next_date, notes)
                SELECT id, done_date, next_date, ''
                FROM companies
                WHERE done_date IS NOT NULL OR next_date IS NOT NULL
            """)


def load_companies():
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT c.id, c.name, i.done_date, i.next_date, i.notes
            FROM companies c
            LEFT JOIN inspections i
            ON i.id = (
                SELECT id
                FROM inspections
                WHERE company_id = c.id
                ORDER BY id DESC
                LIMIT 1
            )
            ORDER BY c.name COLLATE NOCASE
        """)
        return [
            {"id": r[0], "name": r[1], "done": r[2], "next": r[3], "notes": r[4]}
            for r in cur.fetchall()
        ]

def add_company(name):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO companies (name, done_date, next_date) VALUES (?, ?, ?)",
            (name, "", "")
        )
        return cur.lastrowid

def update_company(cid, name):
    with get_connection() as conn:
        conn.execute("""
            UPDATE companies
            SET name=?
            WHERE id=?
        """, (name, cid))

def add_inspection(cid, done_s, next_s, notes):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO inspections (company_id, done_date, next_date, notes) VALUES (?, ?, ?, ?)",
            (cid, done_s, next_s, notes)
        )

def load_inspection_history(cid):
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT done_date, next_date, notes
            FROM inspections
            WHERE company_id=?
            ORDER BY done_date DESC, id DESC
        """, (cid,))
        return [
            {"done": r[0], "next": r[1], "notes": r[2]}
            for r in cur.fetchall()
        ]

def delete_company(cid):
    with get_connection() as conn:
        conn.execute("DELETE FROM inspections WHERE company_id=?", (cid,))
        conn.execute("DELETE FROM companies WHERE id=?", (cid,))

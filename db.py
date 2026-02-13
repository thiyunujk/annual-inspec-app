# db.py
import sqlite3
import os
import json

DEFAULT_DATA_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "AnnualInspectionSystem", "data")
CONFIG_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "AnnualInspectionSystem")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def _can_use_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        return True
    except Exception:
        return False

def _save_data_dir_to_config(path):
    try:
        existing = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    existing = loaded
        existing["data_dir"] = path
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _load_data_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config_data_dir = None
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            val = data.get("data_dir")
            if isinstance(val, str) and val.strip():
                config_data_dir = val.strip()
        except Exception:
            pass

    default_dir = os.environ.get("ANNUAL_INSPECTION_DATA_DIR", DEFAULT_DATA_DIR)

    # 1) Use configured data_dir if it is writable.
    if config_data_dir and _can_use_dir(config_data_dir):
        return config_data_dir

    # 2) Otherwise, fall back to local default and persist it.
    if _can_use_dir(default_dir):
        _save_data_dir_to_config(default_dir)
        return default_dir

    # 3) Last resort: return whatever was configured (or default) and fail later with explicit UI message.
    return config_data_dir or default_dir

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

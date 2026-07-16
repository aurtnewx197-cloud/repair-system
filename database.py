import os
import random
import string
from datetime import datetime

# ---- 数据库模式自动选择 ----
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# 尝试导入 psycopg2（可能不支持 Python 3.14+）
_PSYCOPG2_AVAILABLE = False
try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    pass

if DATABASE_URL and _PSYCOPG2_AVAILABLE:
    # ===== PostgreSQL (Render) =====
    import psycopg2
    import psycopg2.extras

    def get_db():
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn

    def _dict_row(cursor, row):
        """将 PostgreSQL 查询结果转为字典"""
        if row is None:
            return None
        return dict(zip([d[0] for d in cursor.description], row))

    def init_db():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            work_order TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL,
            company_code TEXT NOT NULL,
            building TEXT DEFAULT '',
            room TEXT NOT NULL,
            reporter_name TEXT DEFAULT '',
            reporter_phone TEXT DEFAULT '',
            repair_type TEXT DEFAULT '',
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_to TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()

    def _fetch_all(cursor):
        """将 cursor.fetchall() 结果转为字典列表"""
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _fetch_one(cursor):
        """将 cursor.fetchone() 结果转为字典"""
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [d[0] for d in cursor.description]
        return dict(zip(columns, row))

    # PostgreSQL 参数占位符为 %s
    PLACEHOLDER = "%s"

else:
    # ===== SQLite (本地开发) =====
    import sqlite3

    DATABASE_PATH = os.path.join(os.path.dirname(__file__), "repair.db")

    def get_db():
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def init_db():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order TEXT UNIQUE NOT NULL,
            company TEXT NOT NULL,
            company_code TEXT NOT NULL,
            building TEXT DEFAULT '',
            room TEXT NOT NULL,
            reporter_name TEXT DEFAULT '',
            reporter_phone TEXT DEFAULT '',
            repair_type TEXT DEFAULT '',
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_to TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()

    def _fetch_all(cursor):
        return cursor.fetchall()

    def _fetch_one(cursor):
        return cursor.fetchone()

    PLACEHOLDER = "?"


# ===== 公共函数（SQLite / PostgreSQL 通用） =====

def generate_work_order():
    prefix = "BX"
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = "".join(random.choices(string.digits, k=4))
    return f"{prefix}{date_part}{random_part}"


def create_order(company, company_code, room, description,
                 reporter_name="", reporter_phone="",
                 repair_type="", building=""):
    conn = get_db()
    try:
        cursor = conn.cursor()
        work_order = generate_work_order()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(f"""
        INSERT INTO orders
        (work_order, company, company_code, building, room, reporter_name,
         reporter_phone, repair_type, description, status, created_at, updated_at)
        VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER},
                {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER},
                'pending', {PLACEHOLDER}, {PLACEHOLDER})
        """, (work_order, company, company_code, building, room,
              reporter_name, reporter_phone, repair_type, description, now, now))
        conn.commit()
        return work_order
    finally:
        conn.close()


def get_order(work_order):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM orders WHERE work_order = {PLACEHOLDER}", (work_order,))
        row = _fetch_one(cursor)
        return row
    finally:
        conn.close()


def get_all_orders():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = _fetch_all(cursor)
        return rows
    finally:
        conn.close()


def update_order_status(work_order, status, assigned_to=""):
    conn = get_db()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if assigned_to:
            cursor.execute(
                f"UPDATE orders SET status={PLACEHOLDER}, assigned_to={PLACEHOLDER}, updated_at={PLACEHOLDER} WHERE work_order={PLACEHOLDER}",
                (status, assigned_to, now, work_order)
            )
        else:
            cursor.execute(
                f"UPDATE orders SET status={PLACEHOLDER}, updated_at={PLACEHOLDER} WHERE work_order={PLACEHOLDER}",
                (status, now, work_order)
            )
        conn.commit()
    finally:
        conn.close()


def get_orders_by_date(date_str):
    """获取指定日期的所有工单 (按 created_at 日期筛选)"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM orders WHERE created_at LIKE {PLACEHOLDER} ORDER BY created_at DESC", (f"{date_str}%",))
        rows = _fetch_all(cursor)
        return rows
    finally:
        conn.close()


BUILDINGS = [
    "A栋", "B栋", "C栋", "D栋", "E栋",
    "F栋", "G栋", "H栋", "M栋", "10号楼"
]


def get_buildings():
    return BUILDINGS


def get_companies():
    return [
        {"code": f"E{str(i).zfill(3)}", "name": f"企业{i:03d}"}
        for i in range(1, 301)
    ]

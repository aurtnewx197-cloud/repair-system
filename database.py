import sqlite3
import os
import random
import string
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "repair.db")


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
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


def generate_work_order():
    prefix = "BX"
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{date_part}{random_part}"


def create_order(company, company_code, room, description,
                 reporter_name="", reporter_phone="",
                 repair_type="", building=""):
    conn = get_db()
    cursor = conn.cursor()
    work_order = generate_work_order()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO orders
    (work_order, company, company_code, building, room, reporter_name,
     reporter_phone, repair_type, description, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (work_order, company, company_code, building, room,
          reporter_name, reporter_phone, repair_type, description, now, now))
    conn.commit()
    conn.close()
    return work_order


def get_order(work_order):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE work_order = ?", (work_order,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_order_status(work_order, status, assigned_to=""):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if assigned_to:
        cursor.execute(
            "UPDATE orders SET status=?, assigned_to=?, updated_at=? WHERE work_order=?",
            (status, assigned_to, now, work_order)
        )
    else:
        cursor.execute(
            "UPDATE orders SET status=?, updated_at=? WHERE work_order=?",
            (status, now, work_order)
        )
    conn.commit()
    conn.close()


BUILDINGS = [
    "A栋", "B栋", "C栋", "D栋", "E栋",
    "F栋", "G栋", "H栋", "I栋", "J栋"
]


def get_buildings():
    return BUILDINGS


def get_companies():
    return [
        {"code": f"E{str(i).zfill(3)}", "name": f"\u4f01\u4e1a{i:03d}"}
        for i in range(1, 301)
    ]
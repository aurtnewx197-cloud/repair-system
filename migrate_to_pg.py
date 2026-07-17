#!/usr/bin/env python
"""将本地 SQLite 数据迁移到 Render PostgreSQL"""
import os, sys
from urllib.parse import urlparse

# 读取 Render PostgreSQL 连接地址
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("请先设置环境变量 DATABASE_URL")
    print("从 Render Dashboard → Database → Connections → Internal Database URL 复制")
    sys.exit(1)

# 连接 SQLite
import sqlite3
sqlite_path = os.path.join(os.path.dirname(__file__), "repair.db")
if not os.path.exists(sqlite_path):
    print(f"SQLite 数据库不存在: {sqlite_path}")
    sys.exit(1)

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT * FROM orders ORDER BY id")
rows = sqlite_cursor.fetchall()
print(f"SQLite 中共 {len(rows)} 条工单")

if not rows:
    print("没有数据需要迁移")
    sys.exit(0)

# 连接 PostgreSQL
try:
    import pg8000.dbapi
except ImportError:
    print("请先安装 pg8000: pip install pg8000")
    sys.exit(1)

url = urlparse(DATABASE_URL)
pg_conn = pg8000.dbapi.connect(
    host=url.hostname,
    port=url.port or 5432,
    database=url.path[1:],
    user=url.username,
    password=url.password
)
pg_cursor = pg_conn.cursor()

# 确保表存在
pg_cursor.execute("""
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
    status TEXT NOT NULL DEFAULT '"'"'pending'"'"',
    assigned_to TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
""")
pg_conn.commit()

# 逐条迁移
success = 0
failed = 0
for row in rows:
    try:
        pg_cursor.execute("""
        INSERT INTO orders (work_order, company, company_code, building, room,
            reporter_name, reporter_phone, repair_type, description,
            status, assigned_to, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (work_order) DO NOTHING
        """, (
            row["work_order"], row["company"], row["company_code"],
            row["building"], row["room"], row["reporter_name"],
            row["reporter_phone"], row["repair_type"], row["description"],
            row["status"], row["assigned_to"], row["created_at"], row["updated_at"]
        ))
        pg_conn.commit()
        success += 1
    except Exception as e:
        print(f"  失败: {row['work_order']} - {e}")
        failed += 1

pg_conn.close()
sqlite_conn.close()
print(f"\n迁移完成! 成功: {success}, 失败: {failed}")

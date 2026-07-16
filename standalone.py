# -*- coding: utf-8 -*-
"""独立服务器 - 不依赖任何第三方库，开箱即用"""
import os, io, sys, json, sqlite3, socket, socketserver, random, string, urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from mimetypes import guess_type

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "repair.db")
QR_DIR = os.path.join(BASE, "static", "qrcodes")


# ========== 数据库 ==========
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order TEXT UNIQUE NOT NULL,
        company TEXT NOT NULL,
        company_code TEXT NOT NULL,
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


def gen_wo():
    return "BX" + datetime.now().strftime("%Y%m%d") + "".join(random.choices(string.digits, k=4))


def create_order(company, code, room, desc, name, phone, rtype):
    conn = get_db()
    wo = gen_wo()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO orders (work_order,company,company_code,room,reporter_name,reporter_phone,repair_type,description,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (wo, company, code, room, name, phone, rtype, desc, "pending", now, now))
    conn.commit()
    conn.close()
    return wo


def get_order(wo):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE work_order=?", (wo,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_order(wo, status, assigned=""):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if assigned:
        conn.execute("UPDATE orders SET status=?, assigned_to=?, updated_at=? WHERE work_order=?", (status, assigned, now, wo))
    else:
        conn.execute("UPDATE orders SET status=?, updated_at=? WHERE work_order=?", (status, now, wo))
    conn.commit()
    conn.close()


COMPANIES = {f"E{i:03d}": f"\u4f01\u4e1a{i:03d}" for i in range(1, 301)}
REPAIR_TYPES = ["\u6c34\u7ba1\u7ef4\u4fee", "\u7535\u8def\u7ef4\u4fee", "\u7a7a\u8c03\u7ef4\u4fee", "\u95e8\u7a97\u7ef4\u4fee",
                "\u5899\u9762\u7ef4\u4fee", "\u5730\u677f\u7ef4\u4fee", "\u5bb6\u5177\u7ef4\u4fee", "\u7535\u68af\u7ef4\u4fee",
                "\u6d88\u9632\u7ef4\u4fee", "\u7f51\u7edc\u7ef4\u4fee", "\u5176\u4ed6"]

init_db()


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


def render_html(name, **kw):
    return read_file(os.path.join(BASE, "templates", name)).decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write("[%s] %s - %s\n" % (self.log_date_time_string(), self.client_address[0], format % args))

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Static files
        if path.startswith("/static/"):
            fpath = os.path.join(BASE, path.lstrip("/"))
            if os.path.isfile(fpath):
                ct, _ = guess_type(fpath)
                self.send_response(200)
                self.send_header("Content-Type", ct or "application/octet-stream")
                self.end_headers()
                self.wfile.write(read_file(fpath))
                return
            self.send_error(404)
            return

        # API
        if path == "/api/ip":
            ip = self.client_address[0]
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ip": ip}).encode())
            return

        # Enterprise page
        if path.startswith("/enterprise/"):
            code = path.split("/")[-1].upper()
            name = COMPANIES.get(code)
            if not name:
                return self.redirect("/")
            html = render_html("report_standalone.html", company_name=name, company_code=code)
            self.send_html(html)
            return

        # Track
        if path == "/track":
            html = render_html("track_standalone.html")
            self.send_html(html)
            return

        # Admin
        if path == "/admin":
            orders = get_all()
            rows_html = ""
            for o in orders:
                badge = {"pending": '<span class="badge badge-warning">\u23f3 \u5f85\u5904\u7406</span>',
                         "in_progress": '<span class="badge badge-info">\ud83d\udd27 \u7ef4\u4fee\u4e2d</span>',
                         "completed": '<span class="badge badge-success">\u2705 \u5df2\u5b8c\u6210</span>'}
                s_opts = "".join(f'<option value="{s}" {"selected" if s==o["status"] else ""}>{n}</option>' for s, n in [("pending","\u5f85\u5904\u7406"),("in_progress","\u7ef4\u4fee\u4e2d"),("completed","\u5df2\u5b8c\u6210")])
                rows_html += f"""<tr>
                    <td><code>{o["work_order"]}</code></td>
                    <td>{o["company"]}</td>
                    <td>{o["room"]}</td>
                    <td>{o["repair_type"] or "-"}</td>
                    <td>{o["reporter_name"] or "-"}</td>
                    <td>{o["reporter_phone"] or "-"}</td>
                    <td>{badge.get(o["status"], "")}</td>
                    <td>{o["created_at"][:16]}</td>
                    <td>
                        <form method="POST" action="/admin/update" style="display:flex;gap:4px;flex-wrap:wrap;">
                            <input type="hidden" name="work_order" value="{o["work_order"]}">
                            <select name="status" style="padding:4px;">{s_opts}</select>
                            <input type="text" name="assigned_to" value="{o["assigned_to"]}" placeholder="\u7ef4\u4fee\u4eba\u5458" style="width:80px;padding:4px;">
                            <button type="submit" style="padding:4px 8px;">\u66f4\u65b0</button>
                        </form>
                    </td>
                </tr>"""
            self.send_html(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>\u7ba1\u7406\u540e\u53f0</title><link rel="stylesheet" href="/static/css/style.css"></head><body><div class="container"><div class="header"><h1>\u2699\ufe0f \u5de5\u5355\u7ba1\u7406\u540e\u53f0</h1><p>\u6240\u6709\u62a5\u4fee\u5de5\u5355\u4e00\u89c8 (\u5171{len(orders)}\u6761)</p></div><div class="card"><a href="/" class="btn btn-secondary">\u2190 \u8fd4\u56de\u9996\u9875</a><div class="table-wrapper"><table class="admin-table"><thead><tr><th>\u5de5\u5355\u53f7</th><th>\u4f01\u4e1a</th><th>\u4f4d\u7f6e</th><th>\u7c7b\u578b</th><th>\u62a5\u4fee\u4eba</th><th>\u7535\u8bdd</th><th>\u72b6\u6001</th><th>\u65f6\u95f4</th><th>\u64cd\u4f5c</th></tr></thead><tbody>{rows_html}</tbody></table></div></div></div></body></html>""")
            return

        # Homepage
        self.send_html(render_html("index_standalone.html"))

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        data = urllib.parse.parse_qs(body)
        d = {k: (v[0] if v else "") for k, v in data.items()}

        if path == "/submit":
            code = d.get("company_code", "").upper()
            name = COMPANIES.get(code)
            if not name:
                return self.redirect("/")
            room = d.get("room", "").strip()
            desc = d.get("description", "").strip()
            if not room or not desc:
                return self.redirect(f"/enterprise/{code}")
            wo = create_order(name, code, room, desc, d.get("reporter_name",""), d.get("reporter_phone",""), d.get("repair_type",""))
            order = get_order(wo)
            self.send_html(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>\u63d0\u4ea4\u6210\u529f</title><link rel="stylesheet" href="/static/css/style.css"></head><body><div class="container"><div class="header"><h1>\u2705 \u5de5\u5355\u63d0\u4ea4\u6210\u529f</h1></div><div class="card success-card"><div class="success-icon">\u2705</div><h2>\u60a8\u7684\u62a5\u4fee\u5de5\u5355\u5df2\u751f\u6210</h2><div class="work-order-display"><label>\U0001f4cb \u5de5\u5355\u53f7</label><h1 class="work-order-number">{wo}</h1></div><div class="time-display"><span>\U0001f550</span><span class="time-text">{order["created_at"]}</span></div><p>\u8bf7\u4fdd\u5b58\u5de5\u5355\u53f7\uff0c\u968f\u65f6\u67e5\u8be2\u7ef4\u4fee\u8fdb\u5ea6</p><div class="company-info"><p>\u4f01\u4e1a\uff1a{name}</p></div><div class="action-buttons"><a href="/track" class="btn">\u67e5\u8be2\u8fdb\u5ea6</a><a href="/" class="btn btn-secondary">\u8fd4\u56de\u9996\u9875</a></div></div></div></body></html>""")
            return

        if path == "/track":
            wo = d.get("work_order", "").strip()
            if not wo:
                return self.redirect("/track")
            order = get_order(wo)
            if not order:
                self.send_html(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>\u5de5\u5355\u8ffd\u8e2a</title><link rel="stylesheet" href="/static/css/style.css"></head><body><div class="container"><div class="header"><h1>\U0001f50d \u5de5\u5355\u8ffd\u8e2a</h1></div><div class="card"><div class="alert alert-danger">\u672a\u627e\u5230\u8be5\u5de5\u5355</div><form method="POST"><input type="text" name="work_order" placeholder="\u8bf7\u8f93\u5165\u5de5\u5355\u53f7" required class="form-control"><button type="submit" class="btn">\u67e5\u8be2</button></form></div></div></body></html>""")
                return
            status_map = {"pending":'\u23f3 \u5f85\u5904\u7406', "in_progress":'\ud83d\udd27 \u7ef4\u4fee\u4e2d', "completed":'\u2705 \u5df2\u5b8c\u6210'}
            badge_map = {"pending":"badge-warning","in_progress":"badge-info","completed":"badge-success"}
            self.send_html(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>\u5de5\u5355\u8ffd\u8e2a</title><link rel="stylesheet" href="/static/css/style.css"></head><body><div class="container"><div class="header"><h1>\U0001f50d \u5de5\u5355\u8be6\u60c5</h1></div><div class="card"><table class="detail-table"><tr><th>\u5de5\u5355\u53f7</th><td>{order["work_order"]}</td></tr><tr><th>\u4f01\u4e1a</th><td>{order["company"]}</td></tr><tr><th>\u4f4d\u7f6e</th><td>{order["room"]}</td></tr><tr><th>\u62a5\u4fee\u4eba</th><td>{order["reporter_name"] or "-"}</td></tr><tr><th>\u7ef4\u4fee\u7c7b\u578b</th><td>{order["repair_type"] or "-"}</td></tr><tr><th>\u95ee\u9898\u63cf\u8ff0</th><td>{order["description"]}</td></tr><tr><th>\u5f53\u524d\u72b6\u6001</th><td><span class="badge {badge_map[order["status"]]}">{status_map[order["status"]]}</span></td></tr>{"<tr><th>\u7ef4\u4fee\u4eba\u5458</th><td>"+order["assigned_to"]+"</td></tr>" if order["assigned_to"] else ""}<tr><th>\u63d0\u4ea4\u65f6\u95f4</th><td>{order["created_at"]}</td></tr><tr><th>\u66f4\u65b0\u65f6\u95f4</th><td>{order["updated_at"]}</td></tr></table></div><div class="footer"><a href="/">\u2190 \u8fd4\u56de\u9996\u9875</a></div></div></body></html>""")
            return

        if path == "/admin/update":
            wo = d.get("work_order", "")
            st = d.get("status", "")
            assign = d.get("assigned_to", "")
            if wo and st:
                update_order(wo, st, assign)
            return self.redirect("/admin")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == "__main__":
    PORT = 5002
    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 55)
    print("  \u7269\u4e1a\u62a5\u4fee\u7cfb\u7edf - \u72ec\u7acb\u670d\u52a1\u5668")
    print("=" * 55)
    print(f"  \u7535\u8111\u8bbf\u95ee:  http://127.0.0.1:{PORT}")
    print(f"  \u624b\u673a\u8bbf\u95ee:  http://{ip}:{PORT}")
    print(f"  \u7ba1\u7406\u540e\u53f0:   http://127.0.0.1:{PORT}/admin")
    print("=" * 55)
    print("  Ctrl+C \u505c\u6b62\u670d\u52a1\u5668")
    print("=" * 55)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\u670d\u52a1\u5668\u5df2\u505c\u6b62")
        server.server_close()
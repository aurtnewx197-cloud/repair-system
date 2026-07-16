from flask import Flask, render_template, request, redirect, url_for, flash
import database
import os
import socket

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = "property-repair-system-secret-key-2026"

COMPANIES = database.get_companies()
COMPANY_MAP = {c["code"]: c["name"] for c in COMPANIES}
BUILDINGS = database.get_buildings()

REPAIR_TYPES = [
    "水电维修", "电路维修", "空调维修", "门窗维修",
    "墙面维修", "地板维修", "家具维修", "电梯维修",
    "消防维修", "网络维修", "其他"
]


@app.route("/api/ip")
def api_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    return {"ip": ip}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/report")
def report_page():
    return render_template("report_simple.html",
                           buildings=BUILDINGS,
                           repair_types=REPAIR_TYPES)


@app.route("/report/submit", methods=["POST"])
def report_submit():
    building = request.form.get("building", "").strip()
    room = request.form.get("room", "").strip()
    description = request.form.get("description", "").strip()
    reporter_name = request.form.get("reporter_name", "").strip()
    reporter_phone = request.form.get("reporter_phone", "").strip()
    repair_type = request.form.get("repair_type", "").strip()

    if not building or not room or not description:
        flash("无效的企业二维码，请联系管理员", "danger")
        return redirect(url_for("report_page"))

    work_order = database.create_order(
        company=building,
        company_code=f"BLDG_{building[0]}",
        building=building,
        room=room,
        description=description,
        reporter_name=reporter_name,
        reporter_phone=reporter_phone,
        repair_type=repair_type
    )

    order = database.get_order(work_order)
    return render_template(
        "success.html", work_order=work_order,
        company_name=building,
        created_at=order["created_at"] if order else ""
    )


@app.route("/enterprise/<code>")
def enterprise_report(code):
    name = COMPANY_MAP.get(code)
    if not name:
        flash("无效的企业二维码，请联系管理员", "danger")
        return redirect(url_for("index"))

    room = request.form.get("room", "").strip()
    description = request.form.get("description", "").strip()
    reporter_name = request.form.get("reporter_name", "").strip()
    reporter_phone = request.form.get("reporter_phone", "").strip()
    repair_type = request.form.get("repair_type", "").strip()

    if not room or not description:
        flash("请填写室号和报修内容", "danger")
        return redirect(url_for("enterprise_report", code=company_code))

    work_order = database.create_order(
        company=company_name, company_code=company_code,
        room=room, description=description,
        reporter_name=reporter_name,
        reporter_phone=reporter_phone,
        repair_type=repair_type
    )

    order = database.get_order(work_order)
    return render_template(
        "success.html", work_order=work_order,
        company_name=company_name,
        created_at=order["created_at"] if order else ""
    )


@app.route("/track", methods=["GET", "POST"])
def track():
    if request.method == "POST":
        work_order = request.form.get("work_order", "").strip()
        if not work_order:
            flash("请输入工单号", "warning")
            return render_template("track.html", order=None)
        order = database.get_order(work_order)
        if not order:
            flash("未找到该工单，请检查工单号", "danger")
            return render_template("track.html", order=None)
        return render_template("track.html", order=order)
    return render_template("track.html", order=None)


@app.route("/admin")
def admin():
    from datetime import datetime, timedelta
    from flask import request as flask_req

    def get_wait_level(created_at_str):
        if not created_at_str:
            return "normal", "刚刚", 0
        try:
            created = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        except:
            return "normal", "未知", 0
        minutes = int((datetime.now() - created).total_seconds() / 60)
        hours = minutes // 60
        mins = minutes % 60
        if minutes < 0:
            return "normal", "刚刚", 0
        elif minutes < 30:
            return "normal", f"{minutes}分钟", minutes
        elif minutes < 120:
            return "warning", f"{hours}小时{mins}分钟", minutes
        elif minutes < 240:
            return "danger", f"{hours}小时{mins}分钟", minutes
        else:
            return "overdue", f"{hours}小时{mins}分钟", minutes

    all_orders = database.get_all_orders()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    today_count = sum(1 for o in all_orders if (o["created_at"] or "").startswith(today_str))
    pending_count = sum(1 for o in all_orders if o["status"] == "pending")
    progress_count = sum(1 for o in all_orders if o["status"] == "in_progress")

    overdue_count = 0
    for o in all_orders:
        if o["status"] in ("pending", "in_progress") and o["created_at"]:
            try:
                created = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
                if o["status"] == "pending" and (now - created).total_seconds() > 14400:
                    overdue_count += 1
                elif o["status"] == "in_progress":
                    target = datetime.strptime(o["updated_at"], "%Y-%m-%d %H:%M:%S") if o["updated_at"] else created
                    if o["assigned_to"] and (now - target).total_seconds() > 14400:
                        overdue_count += 1
            except:
                pass

    response_times = []
    for o in all_orders:
        if o["status"] in ("in_progress", "completed") and o["created_at"] and o["updated_at"]:
            try:
                created = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
                updated = datetime.strptime(o["updated_at"], "%Y-%m-%d %H:%M:%S")
                if updated > created:
                    response_times.append(int((updated - created).total_seconds() / 60))
            except:
                pass
    avg_response = "—"
    if response_times:
        avg = sum(response_times) // len(response_times)
        avg_response = f"{avg}分钟" if avg < 60 else f"{avg//60}小时{avg%60}分钟"

    todo_list, doing_list, done_list = [], [], []

    for o in all_orders:
        level, wait_text, wait_minutes = get_wait_level(o["created_at"])
        card = {
            "work_order": o["work_order"],
            "company": o["company"],
            "building": o["building"],
            "room": o["room"],
            "repair_type": o["repair_type"],
            "description": o["description"],
            "reporter_name": o["reporter_name"],
            "reporter_phone": o["reporter_phone"],
            "assigned_to": o["assigned_to"],
            "created_at": o["created_at"],
            "updated_at": o["updated_at"],
            "wait_text": wait_text,
            "wait_level": level,
            "wait_minutes": wait_minutes,
            "is_overdue": level == "overdue",
        }

        if o["status"] == "pending":
            todo_list.append(card)
        elif o["status"] == "in_progress":
            accept_time = o["updated_at"] if o["updated_at"] else o["created_at"]
            _, dur_text, dur_minutes = get_wait_level(accept_time)
            card["accept_time"] = accept_time
            card["duration_text"] = dur_text
            card["duration_minutes"] = dur_minutes
            card["progress"] = 75
            doing_list.append(card)
        elif o["status"] == "completed":
            end_time = o["updated_at"] if o["updated_at"] else o["created_at"]
            _, total_text, total_minutes = get_wait_level(o["created_at"])
            card["completed_at"] = end_time
            card["total_time"] = total_text
            card["total_minutes"] = total_minutes
            card["progress"] = 100
            done_list.append(card)

    todo_list.sort(key=lambda x: (0 if x["is_overdue"] else 1, -x["wait_minutes"]))
    doing_list.sort(key=lambda x: (0 if x.get("duration_minutes", 0) > 240 else 1, -x.get("duration_minutes", 0)))

    return render_template(
        "admin.html",
        todo_list=todo_list,
        doing_list=doing_list,
        done_list=done_list,
        today_count=today_count,
        pending_count=pending_count,
        progress_count=progress_count,
        overdue_count=overdue_count,
        avg_response=avg_response,
        total_count=len(all_orders),
    )


@app.route("/admin/update", methods=["POST"])
def admin_update():
    work_order = request.form.get("work_order", "").strip()
    status = request.form.get("status", "").strip()
    assigned_to = request.form.get("assigned_to", "").strip()

    if not work_order or not status:
        flash("参数不完整", "danger")
        return redirect(url_for("admin"))

    database.update_order_status(work_order, status)
    if assigned_to:
        database.update_order_status(work_order, None, assigned_to)
    return redirect(url_for("admin"))


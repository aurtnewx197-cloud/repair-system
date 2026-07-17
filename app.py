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

    SLA_HOURS = 4  # SLA 超时阈值（小时）

    def is_overdue(order):
        """统一超时判断：创建时间 + SLA 时长 > 当前时间 = 超时"""
        created_str = order["created_at"] or ""
        if not created_str:
            return False
        try:
            created = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
            deadline = created + timedelta(hours=SLA_HOURS)
            return datetime.now() > deadline
        except:
            return False

    def get_wait_info(created_at_str):
        """返回等待时长描述和级别"""
        if not created_at_str:
            return "刚刚", "normal", 0
        try:
            created = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        except:
            return "未知", "normal", 0
        minutes = int((datetime.now() - created).total_seconds() / 60)
        hours = minutes // 60
        mins = minutes % 60
        if minutes < 0:
            return "刚刚", "normal", 0
        elif minutes < 30:
            return f"{minutes}分钟", "normal", minutes
        elif minutes < 120:
            return f"{hours}小时{mins}分钟", "warning", minutes
        elif minutes < 240:
            return f"{hours}小时{mins}分钟", "danger", minutes
        else:
            return f"{hours}小时{mins}分钟", "overdue", minutes

    all_orders = database.get_all_orders()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    today_count = sum(1 for o in all_orders if (o["created_at"] or "").startswith(today_str))
    pending_count = sum(1 for o in all_orders if o["status"] == "pending")
    progress_count = sum(1 for o in all_orders if o["status"] == "in_progress")

    # 统一使用 is_overdue 计算超时数量
    overdue_count = sum(1 for o in all_orders if is_overdue(o) and o["status"] in ("pending", "in_progress"))

    # 平均响应时间
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
        overdue_flag = is_overdue(o)
        wait_text, wait_level, wait_minutes = get_wait_info(o["created_at"])

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
            "wait_level": wait_level,
            "wait_minutes": wait_minutes,
            "is_overdue": overdue_flag,
        }

        if o["status"] == "pending":
            todo_list.append(card)
        elif o["status"] == "in_progress":
            accept_time = o["updated_at"] if o["updated_at"] else o["created_at"]
            dur_text, _, dur_minutes = get_wait_info(accept_time)
            card["accept_time"] = accept_time
            card["duration_text"] = dur_text
            card["duration_minutes"] = dur_minutes
            card["progress"] = 75
            doing_list.append(card)
        elif o["status"] == "completed":
            end_time = o["updated_at"] if o["updated_at"] else o["created_at"]
            total_text, _, total_minutes = get_wait_info(o["created_at"])
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


@app.route("/stats")
@app.route("/stats/<date_str>")
def stats(date_str=None):
    from datetime import datetime, timedelta

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except:
            date_str = datetime.now().strftime("%Y-%m-%d")

    orders = database.get_orders_by_date(date_str)
    total = len(orders)
    pending = sum(1 for o in orders if o["status"] == "pending")
    in_progress = sum(1 for o in orders if o["status"] == "in_progress")
    completed = sum(1 for o in orders if o["status"] == "completed")
    rate = round(completed / total * 100) if total > 0 else 0

    # Previous and next dates
    current = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (current - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "stats.html",
        date_str=date_str,
        total=total,
        pending=pending,
        in_progress=in_progress,
        completed=completed,
        rate=rate,
        orders=orders,
        prev_date=prev_date,
        next_date=next_date,
        today_str=today_str,
    )



@app.route("/admin/delete", methods=["POST"])
def admin_delete():
    work_order = request.form.get("work_order", "").strip()
    if work_order:
        database.delete_order(work_order)
    return redirect(url_for("admin"))


@app.route("/admin/update", methods=["POST"])

@app.route("/admin/push-alert", methods=["POST"])
def admin_push_alert():
    """推送超时工单提醒到飞书/微信"""
    try:
        import notify
        ok, msg = notify.push_overdue_alert()
        if ok:
            flash(msg, "success")
        else:
            flash(msg, "warning" if "未配置" in msg else "danger")
    except Exception as e:
        flash(f"推送失败: {str(e)}", "danger")
    return redirect(url_for("admin"))


def admin_update():
    work_order = request.form.get("work_order", "").strip()
    status = request.form.get("status", "").strip()
    assigned_to = request.form.get("assigned_to", "").strip()

    if not work_order or not status:
        flash("参数不完整", "danger")
        return redirect(url_for("admin"))

    database.update_order_status(work_order, status, assigned_to)
    return redirect(url_for("admin"))


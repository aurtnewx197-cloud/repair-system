"""超时工单推送模块 - 飞书/企业微信"""
import hashlib
import hmac
import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import database

# 从环境变量读取 Webhook URL（在 Render 上设置）
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")
WECHAT_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", "")


def _gen_feishu_sign(timestamp, secret):
    """生成飞书机器人签名"""
    if not secret:
        return ""
    import base64
    string_to_sign = f"{timestamp}\n{secret}"
    return base64.b64encode(hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()).decode("utf-8")


def send_feishu(orders):
    """推送超时工单到飞书群机器人"""
    if not FEISHU_WEBHOOK:
        return False, "未配置 FEISHU_WEBHOOK"

    cards = []
    for o in orders:
        cards.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**工单：{o['work_order']}**\n企业：{o['company']} | 房间：{o['room']}\n报修：{o['description']}\n等待：{o.get('wait_text', '超时')}\n状态：{'待处理' if o['status']=='pending' else '维修中'}"
            }
        })
        cards.append({"tag": "hr"})
    if cards:
        cards.pop()  # 去掉最后一个分隔线

    ts = str(int(time.time()))
    payload = {
        "timestamp": ts,
        "sign": _gen_feishu_sign(ts, FEISHU_SECRET),
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"⚠️ 超时工单提醒 ({len(orders)} 条)"},
                "template": "red"
            },
            "elements": cards + [
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"物业管理系统 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}]}
            ]
        }
    }
    return _post(FEISHU_WEBHOOK, payload)


def send_wechat(orders):
    """推送超时工单到企业微信群机器人"""
    if not WECHAT_WEBHOOK:
        return False, "未配置 WECHAT_WEBHOOK"

    content = f"## ⚠️ 超时工单提醒 ({len(orders)} 条)\n> 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    for o in orders:
        content += f"**工单：{o['work_order']}**\n"
        content += f"企业：{o['company']}　房间：{o['room']}\n"
        content += f"报修：{o['description'][:30]}\n"
        content += f"等待：{o.get('wait_text', '超时')}　状态：{'待处理' if o['status']=='pending' else '维修中'}\n"
        content += "---\n"

    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    return _post(WECHAT_WEBHOOK, payload)


def _post(url, payload):
    """发送 HTTP POST 请求"""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") == 0 or result.get("errcode") == 0:
            return True, "推送成功"
        return False, f"推送失败: {result}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()}"
    except Exception as e:
        return False, str(e)


def get_overdue_orders(all_orders=None):
    """获取所有超时工单（超过4小时未处理）"""
    if all_orders is None:
        all_orders = database.get_all_orders()
    now = datetime.now()
    overdue = []
    for o in all_orders:
        if o["status"] in ("pending", "in_progress") and o["created_at"]:
            try:
                created = datetime.strptime(o["created_at"], "%Y-%m-%d %H:%M:%S")
                if (now - created).total_seconds() > 14400:  # 4小时
                    minutes = int((now - created).total_seconds() / 60)
                    h = minutes // 60
                    m = minutes % 60
                    # 转为 dict 再添加 wait_text（避免 sqlite3.Row 只读问题）
                    item = dict(o)
                    item["wait_text"] = f"{h}小时{m}分钟"
                    overdue.append(item)
            except Exception as e:
                print(f"[notify] get_overdue_orders error: {type(e).__name__}: {e}")
    return overdue


def push_overdue_alert():
    """推送所有超时工单（同时尝试飞书和微信）"""
    orders = get_overdue_orders()
    if not orders:
        return False, "暂无超时工单"
    results = []
    if FEISHU_WEBHOOK:
        ok, msg = send_feishu(orders)
        results.append(f"飞书: {msg}")
    if WECHAT_WEBHOOK:
        ok, msg = send_wechat(orders)
        results.append(f"微信: {msg}")
    if not FEISHU_WEBHOOK and not WECHAT_WEBHOOK:
        return False, "未配置任何推送渠道 (FEISHU_WEBHOOK / WECHAT_WEBHOOK)"
    return True, "\n".join(results)

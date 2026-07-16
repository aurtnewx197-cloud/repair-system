import socket
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "未知"


def print_help(ip):
    print("=" * 60)
    print("  物业报修系统 - 网络访问指南")
    print("=" * 60)
    print()
    print("[方案一] 同一 WiFi 局域网访问")
    print(f"  手机连接公司 WiFi 后访问:")
    print(f"  http://{ip}:5000")
    print()
    print("[方案二] 打印二维码贴在现场")
    print(f"  运行: python generate_qrcodes.py http://{ip}:5000")
    print()
    print("[方案三] 外网访问 (需要域名或内网穿透)")
    print("  A - 使用 ngrok (免费, 无需域名):")
    print("     1. 下载 https://ngrok.com/download")
    print("     2. 运行: ngrok http 5000")
    print("     3. 得到 https://xxxx.ngrok-free.app")
    print("     4. 运行: python generate_qrcodes.py https://xxxx.ngrok-free.app")
    print()
    print("  B - 使用自有域名:")
    print("     1. 域名 A 记录指向你的公网 IP")
    print("     2. 路由器设置端口转发 5000")
    print("     3. 运行: python generate_qrcodes.py http://你的域名:5000")
    print()
    print("[查看所有二维码]")
    print(f"  http://{ip}:5000/static/qrcodes_index.html")
    print("=" * 60)


if __name__ == "__main__":
    ip = get_lan_ip()

    if len(sys.argv) >= 3 and sys.argv[1] == "qr":
        base_url = sys.argv[2]
        print(f"使用地址: {base_url}")
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "generate_qrcodes.py"), base_url])
    elif len(sys.argv) >= 2 and sys.argv[1] == "qr":
        base_url = f"http://{ip}:5000"
        print(f"使用局域网IP: {base_url}")
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "generate_qrcodes.py"), base_url])
    else:
        print_help(ip)
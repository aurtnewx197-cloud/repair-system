"""
二维码生成工具
用法:
    python generate_qrcodes.py                              # 默认 http://localhost:5000
    python generate_qrcodes.py http://192.168.1.18:5000     # 局域网IP
    python generate_qrcodes.py https://wx.baoixiu.com       # 域名
"""
import qrcode
import sys
import os

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
QR_DIR = os.path.join(os.path.dirname(__file__), "static", "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)


def generate_qr(data, filename):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(os.path.join(QR_DIR, filename))


def main():
    print(f"生成 300 家企业二维码")
    print(f"访问地址: {BASE}")
    print("-" * 50)

    for i in range(1, 301):
        code = f"E{i:03d}"
        url = f"{BASE}/enterprise/{code}"
        generate_qr(url, f"{code}.png")
        if i <= 3 or i == 300:
            print(f"  [{code}] {url}")

    # 首页也用二维码 (直接跳到企业001)
    generate_qr(f"{BASE}/enterprise/E001", "_index.png")

    print("-" * 50)
    print(f"已生成 {300} 个企业二维码 + 1 个首页入口码")
    print(f"目录: {QR_DIR}")

    # 生成汇总 HTML
    html = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
            '<title>企业二维码汇总</title>',
            '<style>body{font-family:sans-serif;max-width:1200px;margin:0 auto;padding:20px}',
            'h1{text-align:center}p{text-align:center;color:#888}',
            '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}',
            '.item{text-align:center;padding:12px;border:1px solid #eee;border-radius:8px}',
            '.item img{width:160px;height:160px}.item p{margin:6px 0;font-size:13px;color:#555}</style></head><body>',
            f'<h1>二维码汇总</h1><p>基础地址: {BASE}</p><div class="grid">']

    for i in range(1, 301):
        code = f"E{i:03d}"
        html.append(f'<div class="item"><img src="qrcodes/{code}.png" alt="{code}">'
                    f'<p><strong>{code}</strong><br>企业{i:03d}</p></div>')

    html.append('</div></body></html>')
    index_path = os.path.join(os.path.dirname(__file__), "static", "qrcodes_index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"汇总页面: {index_path}")
    print(f"\n>>> 打开 {BASE}/static/qrcodes_index.html 查看所有二维码 <<<")


if __name__ == "__main__":
    main()
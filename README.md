# 🏢 物业报修系统 - Property Repair System

为 300 家企业提供扫码报修 + 工单管理的一站式解决方案。

## 技术栈

- **后端**: Python Flask
- **数据库**: SQLite
- **前端**: Tailwind CSS (CDN)
- **部署**: Render.com (推荐) / Netlify (需改造)

---

## 🚀 部署指南

### 方案 A: Render.com ⭐（推荐，10 分钟上线）

Render.com 是专门托管 Python Web 应用的平台，**无需修改代码**，SQLite 数据持久化。

#### 1. 推送到 GitHub

`ash
# 在你的电脑上操作
git init
git add .
git commit -m "物业报修系统 v1.0"
# 在 GitHub 创建仓库后
git remote add origin https://github.com/你的用户名/repair-system.git
git push -u origin main
`

#### 2. 在 Render 创建 Web Service

1. 注册 [Render.com](https://render.com)（用 GitHub 登录）
2. 点击 **New +** → **Web Service**
3. 连接你的 GitHub 仓库
4. 填写配置：

| 配置项 | 值 |
|--------|-----|
| **Name** | property-repair-system |
| **Runtime** | Python 3 |
| **Build Command** | pip install -r requirements.txt |
| **Start Command** | gunicorn wsgi:application --bind 0.0.0.0:\ --workers 2 --timeout 120 |
| **Plan** | **Free**（每月 750 小时） |

5. 点击 **Create Web Service**
6. 等待 2-3 分钟构建完成

#### 3. 部署完成

- 访问地址: https://property-repair-system.onrender.com
- 后台管理: https://property-repair-system.onrender.com/admin

#### 4. 后续更新

`ash
git add .
git commit -m "更新功能"
git push
# Render 会自动重新部署
`

---

### 方案 B: Netlify（需改造，不推荐）

⚠️ **Netlify 不适合 Python 后端应用**，存在以下问题：

| 问题 | 说明 |
|------|------|
| SQLite 数据丢失 | Netlify Functions 每次冷启动都是新文件系统，repair.db 会重置 |
| 冷启动延迟 | 每次请求需要 5-10 秒启动 Python 环境 |
| 超时限制 | 免费版函数最长运行 10 秒 |

**如果仍要用 Netlify：**

1. 数据库需要从 SQLite 迁移到 **Supabase**（免费 PostgreSQL）
2. 修改 database.py 连接远程数据库
3. 部署命令:
`ash
# 安装 Netlify CLI
npm install -g netlify-cli
netlify deploy --prod --dir=.
`

不过更推荐直接用 **方案 A (Render.com)**，省时省力。

---

## 📱 功能说明

| 功能 | 路径 |
|------|------|
| 🏠 首页 | / |
| 📝 扫码报修 | /report |
| 🔍 查询进度 | /track |
| 📊 后台看板 | /admin |
| 🏢 企业管理 | /select |

## 📁 项目结构

`
D:\物业报修系统\
├── app.py              # Flask 主应用
├── database.py         # 数据库操作
├── wsgi.py             # Gunicorn 入口
├── requirements.txt    # Python 依赖
├── render.yaml         # Render 部署配置
├── netlify.toml        # Netlify 部署配置
├── templates/          # HTML 模板 (7个)
│   ├── index.html
│   ├── admin.html      # Kanban 看板
│   ├── report.html
│   ├── track.html
│   └── ...
├── static/
│   ├── qrcodes/        # 300 家企业二维码
│   └── qrcodes_index.html
└── repair.db           # SQLite 数据库
`

## ⚙️ 本地运行

`ash
cd D:\物业报修系统
pip install -r requirements.txt
python wsgi.py
# 访问 http://localhost:5000
`

## 🔗 绑定自定义域名

### Render.com
1. 在 Render Dashboard → Settings → Custom Domain
2. 输入你的域名（如 epair.你的公司.com）
3. 在域名 DNS 管理处添加 CNAME 记录指向 property-repair-system.onrender.com

### 注意事项
- 免费版 Render 如果 15 分钟无请求会休眠，下次请求自动唤醒（延迟约 30 秒）
- 如需 24h 在线，可升级到 **Starter 计划**（/月）
- 或配置 [UptimeRobot](https://uptimerobot.com) 每 10 分钟 ping 一次防止休眠

@echo off
cd /d D:\物业报修系统
set PYTHONIOENCODING=utf-8
start /B python app.py > D:\物业报修系统\server.log 2>&1
echo 服务已启动

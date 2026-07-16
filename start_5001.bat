@echo off
chcp 65001 >nul
cd /d D:\物业报修系统
start /B python run.py > server_5001.log 2>&1
echo 服务已启动在端口 5001
echo 访问 http://192.168.1.18:5001
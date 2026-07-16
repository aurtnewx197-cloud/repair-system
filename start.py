import subprocess
import sys
import os

os.chdir("D:\\物业报修系统")

log = open("server.log", "w", encoding="utf-8")
proc = subprocess.Popen(
    [sys.executable, "app.py"],
    stdout=log,
    stderr=log,
    cwd="D:\\物业报修系统",
    creationflags=subprocess.CREATE_NO_WINDOW
)

print(f"服务器已启动，PID: {proc.pid}")
print(f"日志文件: D:\\物业报修系统\\server.log")
print(f"访问地址: http://localhost:5000")

import subprocess, sys, os, time, urllib.request

os.chdir("D:\\物业报修系统")

log = open("server.log", "w", encoding="utf-8")
CREATE_NO_WINDOW = 0x08000000

proc = subprocess.Popen(
    [sys.executable, "-u", "app.py"],
    stdout=log,
    stderr=log,
    cwd="D:\\物业报修系统",
    creationflags=CREATE_NO_WINDOW
)

print(f"PID: {proc.pid}")

# Wait for server to start
for i in range(10):
    time.sleep(1)
    try:
        r = urllib.request.urlopen("http://localhost:5000/", timeout=2)
        print(f"服务器就绪! 状态: {r.status}")
        break
    except:
        print(f"等待启动... ({i+1}/10)")
else:
    print("启动超时，检查日志")
    log.close()
    with open("server.log", "r", encoding="utf-8") as f:
        print(f.read()[-500:])

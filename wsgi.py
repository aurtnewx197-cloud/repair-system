import sys
import os

# 切换到项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

# 初始化数据库
import database
database.init_db()

# 导出 Flask 应用
from app import app as application

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=False)

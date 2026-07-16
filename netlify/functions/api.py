import sys
import os

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

# 初始化数据库
import database
database.init_db()

# 导入 Flask 应用
from app import app

# Netlify Function handler
def handler(event, context):
    """将 Netlify Function 事件转发到 Flask 应用"""
    from flask import Request as FlaskRequest
    
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = event.get('headers', {}) or {}
    query = event.get('queryStringParameters', {}) or {}
    body = event.get('body', '') or ''
    is_base64 = event.get('isBase64Encoded', False)
    
    if is_base64 and body:
        import base64
        body = base64.b64decode(body).decode('utf-8')
    
    # 构建 Flask 测试环境
    query_string = '&'.join(f'{k}={v}' for k, v in query.items()) if query else ''
    
    with app.test_request_context(
        path=path,
        method=method,
        headers=headers,
        query_string=query_string,
        data=body
    ):
        try:
            # 路由分发
            from flask import url_for
            # 手动匹配路由
            rv = app.full_dispatch_request()
            response_body = rv.get_data(as_text=True)
            status_code = rv.status_code
            response_headers = dict(rv.headers)
            
            return {
                'statusCode': status_code,
                'headers': {
                    'Content-Type': response_headers.get('Content-Type', 'text/html; charset=utf-8'),
                    'Access-Control-Allow-Origin': '*',
                },
                'body': response_body
            }
        except Exception as e:
            import traceback
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e), 'traceback': traceback.format_exc()})
            }

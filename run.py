import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

import database
database.init_db()

from app import app
app.config['TEMPLATES_AUTO_RELOAD'] = True

import socket
import socketserver
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler


class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


class LoggingHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(
            "[%s] %s - %s\n" % (
                self.log_date_time_string(),
                self.client_address[0],
                format % args
            )
        )


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    PORT = 5002
    local_ip = get_local_ip()

    server = ThreadedWSGIServer(("0.0.0.0", PORT), LoggingHandler)
    server.set_app(app)

    print("=" * 55)
    print("  \u7269\u4e1a\u62a5\u4fee\u7cfb\u7edf - \u751f\u4ea7\u670d\u52a1\u5668")
    print("=" * 55)
    print(f"  \u7535\u8111\u8bbf\u95ee:  http://127.0.0.1:{PORT}")
    print(f"  \u624b\u673a\u8bbf\u95ee:  http://{local_ip}:{PORT}")
    print(f"  \u7ba1\u7406\u540e\u53f0:   http://127.0.0.1:{PORT}/admin")
    print(f"  \u62a5\u4fee\u6d4b\u8bd5:   http://127.0.0.1:{PORT}/enterprise/E001")
    print()
    print("  [-] \u6b64\u670d\u52a1\u5668\u4e0d\u4f1a\u663e\u793a Flask \u5f00\u53d1\u8b66\u544a")
    print("  [-] \u591a\u7ebf\u7a0b\u5e76\u53d1\u5904\u7406\u8bf7\u6c42")
    print("=" * 55)
    print("  Ctrl+C \u505c\u6b62\u670d\u52a1\u5668")
    print("=" * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\u670d\u52a1\u5668\u5df2\u505c\u6b62")
        server.server_close()
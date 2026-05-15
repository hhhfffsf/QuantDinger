import http.server
import socketserver
import urllib.request
import json
import os

PORT = 8888
API_PORT = 5000
DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy_request("GET")
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            target = self.path
            if not os.path.splitext(target)[1]:
                target = "/index.html"
            orig = self.path
            self.path = target
            try:
                super().do_GET()
            except Exception:
                self.path = orig
                raise
            self.path = orig

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy_request("POST")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy_request("PUT")
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy_request("DELETE")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            self._proxy_request("PATCH")
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self._proxy_request("OPTIONS")

    def _proxy_request(self, method):
        url = f"http://127.0.0.1:{API_PORT}{self.path}"
        body = None
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)

        req = urllib.request.Request(url, data=body, method=method)
        skip_headers = {"host", "connection", "content-length"}
        for k, v in self.headers.items():
            if k.lower() not in skip_headers:
                req.add_header(k, v)

        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in {"transfer-encoding", "connection"}:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in {"transfer-encoding", "connection"}:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
        print(f"Frontend serving at http://0.0.0.0:{PORT}")
        print(f"API proxy: /api/* -> http://127.0.0.1:{API_PORT}")
        httpd.serve_forever()
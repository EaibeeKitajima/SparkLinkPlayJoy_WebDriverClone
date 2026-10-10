#!/usr/bin/env python3
"""Zero-dependency, loopback-only local web driver server."""
import argparse
import http.server
import json
import pathlib
import urllib.parse
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent
WEB = ROOT / "web"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Permissions-Policy", "hid=(self)")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "connect-src 'self' blob: data:; object-src 'none'; frame-src 'self'; base-uri 'self'")
        super().end_headers()

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def api_response(self, path):
        endpoint = path.rstrip("/").split("/")[-1]
        if endpoint == "getAllDevices":
            return json.loads((WEB / "local-data/device-catalog-response.json").read_text())
        if endpoint.startswith("getAxisList"):
            cached = WEB / "local-data" / (endpoint + ".json")
            if cached.is_file():
                return json.loads(cached.read_text())
            return {"code": 200, "data": []}
        if endpoint == "getKeyboardFirmware":
            return {"code": 200, "data": None, "message": "本地版请使用本地固件文件"}
        if endpoint == "list":
            return {"code": 200, "data": {"list": [], "total": 0}}
        return {"code": 503, "message": "本地版不提供原站云服务，请使用本地文件功能"}

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/local-api/"):
            return self.json_response(self.api_response(path))
        if path == "/health":
            return self.json_response({"ok": True, "edition": "local", "deviceAdmission": "all-browser-accessible-hid"})
        if path == "/connect" or path.startswith("/device/"):
            self.path = "/index.html"
        for product in ("keyboard", "keyboardv3", "mouse"):
            prefix = "/" + product
            if path == prefix or path.startswith(prefix + "/") and not pathlib.PurePosixPath(path).suffix:
                self.path = prefix + "/index.html"
                break
        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/local-api/"):
            return self.json_response(self.api_response(path))
        self.send_error(405)


def main():
    parser = argparse.ArgumentParser(description="星闪悦动本地驱动")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="在默认浏览器中打开驱动")
    args = parser.parse_args()
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as error:
        parser.exit(1, f"启动失败：{error}\n可用 --port 8766 更换端口。\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"星闪悦动本地版：{url}\n请使用 Chrome / Edge。按 Ctrl+C 停止。", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

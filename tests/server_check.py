#!/usr/bin/env python3
import json
import urllib.request

origin = "http://127.0.0.1:8765"
for path in ("/", "/connect", "/device/mouse", "/keyboard", "/keyboard/device", "/keyboardv3", "/mouse"):
    with urllib.request.urlopen(origin + path) as response:
        assert response.status == 200, path
        assert response.headers["Permissions-Policy"] == "hid=(self)"
        assert "connect-src 'self'" in response.headers["Content-Security-Policy"]
        assert b"/local/boot.js" in response.read(), path
for path in ("/health", "/local-data/device-catalog.json", "/local-api/device/api/v1/getAllDevices", "/local-api/device/api/v1/getAxisList"):
    with urllib.request.urlopen(origin + path) as response:
        data = json.load(response)
        assert data, path
with urllib.request.urlopen(origin + "/local/fonts/iconfont.woff2") as response:
    assert len(response.read()) > 10000
print("Local HTTP routes, assets, API snapshots and loopback headers passed")

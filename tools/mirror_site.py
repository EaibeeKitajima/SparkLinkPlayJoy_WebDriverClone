#!/usr/bin/env python3
"""Download public same-origin frontend assets, including lazy-loaded chunks."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

ORIGIN = "https://hub.xsyd.top/"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "web"
ASSET = re.compile(r'''(?:["'`(])((?:/assets/|\./|/)?[^"'`\s()<>]*\.(?:js|css|svg|png|jpe?g|webp|gif|ico|woff2?|ttf|otf|wasm|json|bin|hex|zip|mp4|webm)(?:\?[^"'`\s()<>]*)?)["'`) ]''')


def references(data, url):
    refs = set()
    for match in ASSET.finditer(data):
        value = match.group(1)
        if value.startswith(("data:", "blob:", "http:", "https:", "//")):
            continue
        if not re.search(r'-[\w-]{6,}\.[a-z0-9]+(?:\?|$)', value) and not value.startswith("/") and pathlib.PurePosixPath(value).name not in ("startup.css", "miniLogo.svg", "miniLogo.png", "preload-manifest.json", "index.html"):
            continue
        if "/assets/default-" in value or "/assets/connect/" in value:
            continue
        base = url
        if value.startswith(("js/", "css/", "assets/")):
            product = urllib.parse.urlparse(url).path.split("/")[1]
            base = urllib.parse.urljoin(ORIGIN, product + "/") if product in ("keyboard", "mouse", "keyboardv3") else ORIGIN
        resolved = urllib.parse.urljoin(base, value)
        parsed = urllib.parse.urlparse(resolved)
        if parsed.netloc == "hub.xsyd.top" and not any(c in parsed.path for c in "{}$"):
            refs.add(urllib.parse.urlunparse(parsed._replace(query="", fragment="")))
    return refs


def download(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip("/") or "index.html"
    if path.endswith("/"):
        path += "index.html"
    target = (DEST / path).resolve()
    if not target.is_relative_to(DEST.resolve()):
        raise ValueError("Invalid asset path")
    if target.is_file():
        data = target.read_bytes()
        refs = references(data.decode("utf-8", errors="replace"), url) if path.endswith(("js", "css", "html", "json")) else set()
        return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}, refs
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                mime = response.headers.get("Content-Type", "")
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip("/") or "index.html"
    if path.endswith("/"):
        path += "index.html"
    target = (DEST / path).resolve()
    if not target.is_relative_to(DEST.resolve()):
        raise ValueError("Invalid asset path")
    if not path.endswith("index.html") and "text/html" in mime:
        raise ValueError("SPA fallback, not an asset")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    refs = references(data.decode("utf-8", errors="replace"), url) if path.endswith(("js", "css", "html", "json")) else set()
    return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}, refs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra", action="append", default=[])
    args = parser.parse_args()
    pending = {ORIGIN, *(urllib.parse.urljoin(ORIGIN, value) for value in args.extra)}
    seen, records, errors = set(), [], []
    DEST.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        while pending:
            batch = sorted(pending - seen)
            pending.clear()
            seen.update(batch)
            futures = {pool.submit(download, url): url for url in batch}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    record, refs = future.result()
                    records.append(record)
                    pending.update(refs - seen)
                    print(f'{record["path"]}: {record["bytes"]} bytes', flush=True)
                except Exception as error:
                    errors.append({"url": url, "error": str(error)})
                    print(f"SKIP {url}: {error}", flush=True)
    (ROOT / "upstream-manifest.json").write_text(json.dumps({"origin": ORIGIN, "assets": sorted(records, key=lambda record: record["path"]), "skipped": errors}, ensure_ascii=False, indent=2) + "\n")
    print(f"Downloaded {len(records)} assets; skipped {len(errors)} references")


if __name__ == "__main__":
    main()

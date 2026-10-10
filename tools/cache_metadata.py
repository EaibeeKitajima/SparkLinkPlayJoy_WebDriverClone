#!/usr/bin/env python3
"""Refresh public offline metadata without sending any device/user identity."""
import concurrent.futures
import json
import pathlib
import re
import subprocess
import urllib.request
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
with zipfile.ZipFile(root / "upstream-originals.zip") as archive:
    source = archive.read("assets/ConnectPage-CxZ4_QhO.js").decode()
api_key = re.search(r'_a=`([^`]+)`', source).group(1)
aes_key = re.search(r'va=`([^`]+)`', source).group(1)
dest = root / "web/local-data"


def fetch(endpoint, base="https://api.sparklinkplayjoy.com/api/v1"):
    req = urllib.request.Request(base + "/" + endpoint, headers={"Xs-API-Key": api_key, "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    data = json.loads(raw)
    return endpoint, data, raw


jobs = [(name, "https://api.sparklinkplayjoy.com/api/v1") for name in ("getAxisList", "getAxisListV2", "getAxisListV3")]
jobs.append(("getAllDevices", "https://testadmin.sparklinkplayjoy.com/api/v1"))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for future in [pool.submit(fetch, name, base) for name, base in jobs]:
        try:
            endpoint, data, raw = future.result()
            if endpoint != "getAllDevices":
                if isinstance(data, dict) and data.get("code") == 200 and data.get("data"):
                    (dest / (endpoint + ".json")).write_bytes(raw)
                    print(endpoint, "cached", len(raw), "bytes", flush=True)
                else:
                    print(endpoint, "not available without model parameters", flush=True)
                continue
            encrypted = data if isinstance(data, str) else data["data"]
            js = """
            const {createDecipheriv}=require('node:crypto'); let s='';
            process.stdin.on('data',c=>s+=c); process.stdin.on('end',()=>{
              const {key,encrypted}=JSON.parse(s),b=Buffer.from(encrypted,'base64');
              const d=createDecipheriv('aes-256-cbc',Buffer.from(key),b.subarray(0,16));
              process.stdout.write(Buffer.concat([d.update(b.subarray(16)),d.final()]).toString());
            });
            """
            result = subprocess.run(["node", "-e", js], input=json.dumps({"key": aes_key, "encrypted": encrypted}), capture_output=True, text=True, check=True)
            updated = json.loads(result.stdout)
            base_catalog = json.loads((dest / "device-catalog.json").read_text())
            base_catalog.update(updated)
            (dest / "device-catalog.json").write_text(json.dumps(base_catalog, ensure_ascii=False, indent=2) + "\n")
            print("Merged current catalog:", len(updated), "identities;", len(base_catalog), "total", flush=True)
        except Exception as error:
            print(type(error).__name__, str(error), flush=True)

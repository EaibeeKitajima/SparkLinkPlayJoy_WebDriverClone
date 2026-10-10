#!/usr/bin/env python3
"""Cache the public device definitions used by the original driver."""
import json
import pathlib
import re
import subprocess
import urllib.request

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "web/assets/ConnectPage-CxZ4_QhO.js").read_text()
api_key = re.search(r'_a=`([^`]+)`', source).group(1)
aes_key = re.search(r'va=`([^`]+)`', source).group(1)
request = urllib.request.Request("https://api.sparklinkplayjoy.com/api/v1/getAllDevices", headers={"Xs-API-Key": api_key, "User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(request, timeout=45) as response:
    raw = response.read()
data = json.loads(raw)
encrypted = data if isinstance(data, str) else data["data"]
js = """
const {createDecipheriv} = require('node:crypto');
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const {key, encrypted} = JSON.parse(input);
  const bytes = Buffer.from(encrypted, 'base64');
  const decipher = createDecipheriv('aes-256-cbc', Buffer.from(key), bytes.subarray(0, 16));
  const result = Buffer.concat([decipher.update(bytes.subarray(16)), decipher.final()]);
  process.stdout.write(JSON.stringify(JSON.parse(result.toString()), null, 2));
});
"""
decoded = subprocess.run(["node", "-e", js], input=json.dumps({"key": aes_key, "encrypted": encrypted}), capture_output=True, text=True, check=True).stdout
directory = root / "web/local-data"
directory.mkdir(parents=True, exist_ok=True)
(directory / "device-catalog.json").write_text(decoded + "\n")
(directory / "device-catalog-response.json").write_bytes(raw)
print(f"Cached {len(json.loads(decoded))} public device identities")

#!/usr/bin/env python3
"""Validate local bundle references; never fetch or replace missing resources."""
import json
import pathlib
import urllib.parse
from mirror_site import references

root = pathlib.Path(__file__).resolve().parents[1]
web = root / "web"
missing = {}
for path in web.rglob("*"):
    if path.suffix not in (".js", ".css", ".html", ".json") or "local" in path.relative_to(web).parts:
        continue
    source = path.read_text(errors="replace")
    for url in references(source, "https://hub.xsyd.top/" + path.relative_to(web).as_posix()):
        relative = urllib.parse.urlparse(url).path.lstrip("/")
        if not (web / relative).is_file():
            missing.setdefault(relative, []).append(path.relative_to(web).as_posix())
status = {
    "complete": not missing,
    "missingScripts": sum(path.endswith(".js") for path in missing),
    "missingStyles": sum(path.endswith(".css") for path in missing),
    "missingAssets": len(missing),
    "missing": dict(sorted(missing.items())),
}
(web / "local/resource-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")
(root / "missing-assets.txt").write_text("\n".join("https://hub.xsyd.top/" + path for path in sorted(missing)) + "\n")
print(f'{status["missingScripts"]} scripts, {status["missingStyles"]} styles, {status["missingAssets"]} total missing assets')
raise SystemExit(0 if status["complete"] else 1)

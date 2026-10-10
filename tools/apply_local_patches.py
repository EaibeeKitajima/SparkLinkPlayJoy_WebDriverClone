#!/usr/bin/env python3
"""Auditable adaptations of upstream production bundles for local use."""
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
ARCHIVE = ROOT / "upstream-originals.zip"
originals = {}
if ARCHIVE.exists():
    with zipfile.ZipFile(ARCHIVE) as archive:
        originals = {name: archive.read(name).decode("utf-8-sig") for name in archive.namelist()}


def patch(path, transform):
    relative = str(path.relative_to(WEB))
    source = originals.get(relative, path.read_text(encoding="utf-8-sig"))
    updated = transform(source)
    if updated != source:
        originals[relative] = source
        path.write_text(updated)


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Patch signature changed: {before[:100]}")
    return source.replace(before, after, 1)


def common(source):
    source = source.replace('title:`星闪悦动`', 'title:`星闪悦动 · 本地版`')
    source = source.replace("openDeviceListOnline:!0", "openDeviceListOnline:!1")
    for feature in ("showLogin", "showVideo", "showActivity", "showEcho"):
        source = source.replace(feature + ":!0", feature + ":!1")
    source = source.replace("https://test.engineapi.sparklinkplayjoy.com", "/local-api/engine")
    source = source.replace("https://engineapi.sparklinkplayjoy.com", "/local-api/engine")
    source = source.replace("https://testadmin.sparklinkplayjoy.com/api/v1", "/local-api/device/api/v1")
    source = source.replace("https://api.sparklinkplayjoy.com", "/local-api/device")
    return source


def without_version_poll(source, start, end):
    source = common(source)
    first = source.index(start)
    last = source.index(end, first)
    return source[:first] + start + "}" + source[last:]


def home(source):
    source = common(source)
    source = 'import { chooseProvider as localChooseProvider, deviceDescriptor as localDescriptor, getAdmissionCatalog } from "/local/device-policy.mjs";\nconst localCatalog = await getAdmissionCatalog();\n' + source
    source = replace_once(source, "async function xa(){try{", "async function xa(){return localCatalog;try{")
    start = source.index("function ao(e,t){")
    end = source.index("function oo(e,t){", start)
    source = source[:start] + "function ao(e,t){let n=localChooseProvider(e,t,localCatalog);if(!n)return{ok:!1,reason:`unsupported-device`};let r=io(e,[localDescriptor(e)]);return{device:r,ok:!0,productId:n.productId}}" + source[end:]
    source = replace_once(source, "e.requestDevice({filters:r})", "e.requestDevice({filters:[]})")
    return source


def keyboard(source):
    source = common(source)
    source = 'import { getLocalCatalog as localGetCatalog } from "/local/device-policy.mjs";\n' + source
    source = replace_once(source, "getDeviceCatalog:async()=>{", "getDeviceCatalog:async()=>{return localGetCatalog();")
    return source


def sdk_v2(source):
    source = common(source)
    source = 'import { selectCollection as localCollection } from "/local/device-policy.mjs";\n' + source
    source = replace_once(source, "navigator.hid.requestDevice({filters:this.configs})", "navigator.hid.requestDevice({filters:[]})")
    start = source.index("filterHIDDevices=e=>")
    end = source.index("updateDeviceStatus(", start)
    source = source[:start] + "filterHIDDevices=e=>e;" + source[end:]
    source = replace_once(source, "usage:this.usage[0],usagePage:e.collections?.[0]?.usagePage||-1", "usage:localCollection(e).usage,usagePage:localCollection(e).usagePage")
    return source


def sdk_v3(source):
    source = common(source)
    source = 'import { selectCollection as localCollection, getLocalCatalog as localGetCatalog } from "/local/device-policy.mjs";\n' + source
    source = replace_once(source, "function Nd(e){let t=e.collections[0];", "function Nd(e){let t=localCollection(e);")
    source = replace_once(source, "filters:await lf()", "filters:[]")
    source = replace_once(source, "getDeviceCatalog:async()=>Qd(await Xd.get(nf,`/getAllDevices`,{},{}))", "getDeviceCatalog:async()=>localGetCatalog()")
    return source


def mouse(source):
    source = common(source)
    source = 'import { selectCollection as localCollection, getLocalCatalog as localGetCatalog } from "/local/device-policy.mjs";\n' + source
    source = replace_once(source, "return mn(yield dn.get(pn,`/getAllDevices`))", "return yield localGetCatalog()")
    start = source.index("matchesFilters(e){")
    end = source.index("requireDevice(e){", start)
    source = source[:start] + "matchesFilters(e){return!0}" + source[end:]
    source = replace_once(source, "e.hidApi.requestDevice({filters:e.filters})", "e.hidApi.requestDevice({filters:[]})")
    before = "let t=e.collections[0]"
    source = source.replace(before, "let t=localCollection(e)")
    start = source.index("toWebHidDeviceInfo(e){")
    end = source.index("createMouseClient(e,t){", start)
    source = source[:start] + "toWebHidDeviceInfo(e){let c=localCollection(e);return{...e,collections:e.collections??[],data:`rawDevice`in e?e.rawDevice:e,id:e.id,productId:e.productId,productName:e.productName,usage:c.usage,usagePage:c.usagePage,vendorId:e.vendorId}}" + source[end:]
    before = ".filter(t=>Qt(e.mouseCatalog).some(e=>t.vendorId===e.vendorId&&t.productId===e.productId&&t.collections.some(t=>t.usagePage===e.usagePage&&t.usage===e.usage)))"
    source = replace_once(source, before, "")
    return source


def html(source):
    source = source.replace("<head>", '<head>\n    <link rel="stylesheet" href="/local/local.css">\n    <script src="/local/boot.js"></script>', 1)
    source = source.replace("<title>星闪悦动</title>", "<title>星闪悦动 · 本地版</title>")
    return source


special = {
    "assets/ConnectPage-CxZ4_QhO.js": home,
    "keyboard/js/locale-DmD0egYz.js": keyboard,
    "keyboard/js/esm-BSNVEyo2.js": sdk_v2,
    "keyboardv3/js/keyboard-api-B0AHPMTB.js": sdk_v3,
    "mouse/js/locales-oS-ICJqT.js": mouse,
    "assets/index-BWPZnG1c.js": lambda source: without_version_poll(source, "function k(){", "function A(){"),
    "keyboard/js/main-DjX7mXN9.js": lambda source: without_version_poll(source, "function ec(){", "function tc(e,t){"),
}
for path in sorted(WEB.rglob("*.js")):
    if "local" not in path.parts:
        patch(path, special.get(str(path.relative_to(WEB)), common))
for path in [WEB / "index.html", *(WEB / p / "index.html" for p in ("keyboard", "mouse", "keyboardv3"))]:
    patch(path, html)
for path in WEB.rglob("*.css"):
    def css(source):
        source = source.replace("//at.alicdn.com/t/c/font_5026511_ty3l6e5ijqm.woff2?t=1786692639287", "/local/fonts/iconfont.woff2")
        return re.sub(r',url\("//at\.alicdn\.com/t/c/font_5026511_ty3l6e5ijqm\.(?:woff|ttf)\?t=1786692639287"\) format\("(?:woff|truetype)"\)', '', source)
    patch(path, css)
with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name, source in sorted(originals.items()):
        archive.writestr(name, source)
print(f"Applied local patches; retained {len(originals)} original bundles in {ARCHIVE.name}")

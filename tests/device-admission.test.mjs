import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import test from "node:test";
import { chooseProvider, deviceDescriptor, selectCollection, getAdmissionCatalog, getLocalCatalog, PROFILE_KEY, CATALOG_KEY, validateCatalog } from "../web/local/device-policy.mjs";

function storage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
}
const device = { vendorId: 65500, productId: 60123, productName: "Unknown keyboard", collections: [{ usage: 2, usagePage: 1 }, { usage: 7, usagePage: 0xffab, outputReports: [{reportId: 1}] }] };
const providers = ["keyboard", "mouse", "keyboardv3"].map(productId => ({ productId, filters: [], resolveFilters: async () => [], matchesDevice: () => false, provider: { matchesDevice: () => false } }));
function homeRuntime(selected = storage()) {
  const source = readFileSync(new URL("../web/assets/ConnectPage-CxZ4_QhO.js", import.meta.url), "utf8");
  const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
  const runtime = vm.createContext({
    localChooseProvider: (d, p, c) => chooseProvider(d, p, c, selected), localDescriptor: deviceDescriptor,
    localCatalog: {}, Xa: new WeakMap(), $a: e => e, $: e => e,
    ta: (d, f) => f.vendorId === d.vendorId && f.productId === d.productId,
  });
  vm.runInContext(section("async function no(e)", "function ro(e)") + section("function ro(e)", "function so(") + section("async function co(e,t)", "function uo(e,t,n,r)"), runtime);
  return runtime;
}

test("unknown VID/PID is admitted and receives the selected protocol", async () => {
  const runtime = homeRuntime();
  const result = await runtime.co({ getDevices: async () => [device] }, providers);
  assert.equal(result.ok, true);
  assert.equal(result.devices.length, 1);
  assert.equal(result.devices[0].productId, "keyboard");
  assert.equal(result.devices[0].device.vendorId, device.vendorId);
});
test("picker requests all browser-accessible HID interfaces", async () => {
  let options;
  const result = await homeRuntime().lo({ requestDevice: async input => { options = input; return [device]; } }, providers);
  assert.deepEqual([...options.filters], []);
  assert.equal(result.devices.length, 1);
});
test("permission denial and cancellation still reach the original error flow", async () => {
  const runtime = homeRuntime();
  assert.equal((await runtime.lo({ requestDevice: async () => [] }, providers)).reason, "device-not-found");
  assert.equal((await runtime.lo({ requestDevice: async () => { throw {name: "NotAllowedError"}; } }, providers)).reason, "permission-denied");
});
test("two devices and overlapping provider filters do not cause a provider conflict", async () => {
  const overlapping = providers.map(p => ({ ...p, matchesDevice: () => true, provider: {...p.provider, matchesDevice: () => true} }));
  const result = await homeRuntime().co({ getDevices: async () => [device, {...device}] }, overlapping);
  assert.equal(result.ok, true);
  assert.equal(result.devices.length, 2);
});
test("manual protocol override admits unknown mouse and V3 devices", () => {
  for (const profile of ["mouse", "keyboardv3", "keyboard"]) {
    const selected = storage({ [PROFILE_KEY]: profile });
    assert.equal(chooseProvider(device, providers, {}, selected).productId, profile);
  }
});
test("automatic protocol choice preserves catalog V3 and mouse definitions", () => {
  const id = `${device.vendorId}-${device.productId}`;
  assert.equal(chooseProvider(device, providers, {[id]: [{protocol_version:"v3"}]}, storage()).productId,"keyboardv3");
  assert.equal(chooseProvider(device, providers, {[id]: [{target_id:0}]}, storage()).productId,"mouse");
});
test("handoff describes the vendor collection rather than the protected keyboard collection", () => {
  assert.equal(selectCollection(device).usagePage, 0xffab);
  assert.equal(deviceDescriptor(device).usage, 7);
});
test("custom catalog remains local and unknown mouse targets are available for probing", async () => {
  const id = `${device.vendorId}-${device.productId}`;
  const local = storage({[CATALOG_KEY]: JSON.stringify({"1-2":[{protocol_version:"v3"}]})});
  const requests = [];
  const fetcher = async url => { requests.push(url); return {ok:true,json:async()=>({})}; };
  const catalog = await getLocalCatalog({fetcher, storage:local, hid:{getDevices:async()=>[device]}});
  assert.deepEqual(catalog[id].map(e=>e.target_id), [0,1,2,3]);
  assert.equal(catalog["1-2"][0].protocol_version,"v3");
  assert.deepEqual(requests,["/local-data/device-catalog.json"]);
  const admission = await getAdmissionCatalog({fetcher, storage:local});
  assert.equal(admission[id],undefined);
});
test("catalog import rejects malformed identifiers and target addresses", () => {
  assert.throws(()=>validateCatalog({"65536-1":[{}]}));
  assert.throws(()=>validateCatalog({"1-2":[{target_id:256}]}));
  assert.throws(()=>validateCatalog([]));
});
test("V2 and V3 runtime filters no longer exclude devices by VID/PID or usage", () => {
  const v2=readFileSync(new URL("../web/keyboard/js/esm-BSNVEyo2.js",import.meta.url),"utf8");
  const v3=readFileSync(new URL("../web/keyboardv3/js/keyboard-api-B0AHPMTB.js",import.meta.url),"utf8");
  const mouse=readFileSync(new URL("../web/mouse/js/locales-oS-ICJqT.js",import.meta.url),"utf8");
  const filter=vm.runInNewContext(v2.slice(v2.indexOf("filterHIDDevices=e=>")+"filterHIDDevices=".length,v2.indexOf("updateDeviceStatus(",v2.indexOf("filterHIDDevices=e=>")) - 1));
  assert.deepEqual(filter([device]),[device]);
  assert.ok(v3.includes("filters:[],lateToleranceMs"));
  assert.ok(mouse.includes("matchesFilters(e){return!0}"));
});

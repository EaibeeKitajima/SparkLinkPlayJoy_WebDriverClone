/** Local admission policy. WebHID permissions and protocol handshakes remain intact. */
export const PROFILE_KEY = "xsyd:local:driver-profile";
export const CATALOG_KEY = "xsyd:local:custom-catalog";
const PROFILES = new Set(["auto", "keyboard", "keyboardv3", "mouse"]);

export function getProfile(storage = globalThis.localStorage) {
  const value = storage?.getItem(PROFILE_KEY);
  return PROFILES.has(value) ? value : "auto";
}

export function selectCollection(device) {
  const collections = device.collections ?? device.data?.collections ?? [];
  return collections.find(c => c.usagePage === 0xffb0 && c.usage === 1)
    ?? collections.find(c => c.usagePage >= 0xff00 && (c.outputReports?.length || c.featureReports?.length))
    ?? collections.find(c => c.usagePage >= 0xff00)
    ?? collections[0]
    ?? { usagePage: device.usagePage ?? 0, usage: device.usage ?? 0 };
}

export function chooseProvider(device, providers, catalog = {}, storage = globalThis.localStorage) {
  const profile = getProfile(storage);
  if (profile !== "auto") return providers.find(p => p.productId === profile);
  const definitions = catalog[`${device.vendorId}-${device.productId}`];
  const entries = Array.isArray(definitions) ? definitions : definitions ? [definitions] : [];
  if (entries.some(e => e.target_id !== undefined)) return providers.find(p => p.productId === "mouse");
  if (entries.some(e => e.protocol_version === "v3")) return providers.find(p => p.productId === "keyboardv3");
  const matched = providers.filter(p => p.provider.matchesDevice(device, p.filters));
  if (matched.length === 1) return matched[0];
  if (/mouse|鼠标|receiver|dongle/i.test(device.productName ?? "")) return providers.find(p => p.productId === "mouse");
  return providers.find(p => p.productId === "keyboard");
}

export function deviceDescriptor(device) {
  const c = selectCollection(device);
  return {
    vendorId: device.vendorId, productId: device.productId,
    productName: device.productName, usagePage: c.usagePage, usage: c.usage,
  };
}

export function validateCatalog(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("设备目录必须是 JSON 对象");
  const result = {};
  for (const [key, entries] of Object.entries(value)) {
    const match = /^(\d+)-(\d+)$/.exec(key);
    if (!match || match.slice(1).some(n => Number(n) > 65535)) throw new Error(`设备标识无效：${key}`);
    const list = Array.isArray(entries) ? entries : [entries];
    if (!list.length || list.some(e => !e || typeof e !== "object" || Array.isArray(e))) throw new Error(`设备配置无效：${key}`);
    for (const entry of list) {
      if (entry.target_id !== undefined) {
        const target = Number(entry.target_id);
        if (!Number.isInteger(target) || target < 0 || target > 255) throw new Error(`鼠标目标地址无效：${key}`);
      }
    }
    result[key] = list;
  }
  return result;
}

export async function getAdmissionCatalog({ fetcher = globalThis.fetch, storage = globalThis.localStorage } = {}) {
  const response = await fetcher("/local-data/device-catalog.json");
  if (!response.ok) throw new Error("无法读取本地设备目录");
  const base = await response.json();
  let custom = {};
  try { custom = validateCatalog(JSON.parse(storage?.getItem(CATALOG_KEY) || "{}")); } catch { /* Ignore corrupt saved settings. */ }
  return { ...base, ...custom };
}

export async function getLocalCatalog({ fetcher = globalThis.fetch, hid = globalThis.navigator?.hid, storage = globalThis.localStorage } = {}) {
  const catalog = await getAdmissionCatalog({ fetcher, storage });
  const devices = await hid?.getDevices() ?? [];
  for (const device of devices) {
    const key = `${device.vendorId}-${device.productId}`;
    const existing = catalog[key];
    const entries = Array.isArray(existing) ? existing : existing ? [existing] : [];
    if (entries.some(e => e.target_id !== undefined)) continue;
    // Unknown mouse targets are probed by the original read-only protocol handshake.
    // Users can import exact definitions for devices with different chip addresses.
    catalog[key] = [...entries, ...[0, 1, 2, 3].map(target => ({
      board_id: "local", microchip_id: "local", type: "master_mcu",
      name: device.productName ?? "本地设备", target_id: target, master_mcu_target_id: target,
    }))];
  }
  return catalog;
}

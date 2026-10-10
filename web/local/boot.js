(() => {
  if (window.parent !== window) return;
  const profileKey = "xsyd:local:driver-profile";
  const catalogKey = "xsyd:local:custom-catalog";
  const rootPage = ["/", "/connect", "/connect/"].includes(location.pathname);
  window.addEventListener("DOMContentLoaded", () => {
    const bar = document.createElement("aside");
    bar.className = "local-bar";
    bar.setAttribute("aria-label", "本地驱动设置");
    bar.innerHTML = `<div class="local-identity"><span class="local-dot"></span><strong>本地版</strong><span>设备准入已开放</span></div>
      <div class="local-controls">${rootPage ? `<label for="local-profile">驱动协议</label><select id="local-profile"><option value="auto">自动选择（未知设备默认键盘 V2）</option><option value="keyboard">键盘 V2</option><option value="keyboardv3">键盘 V3</option><option value="mouse">鼠标</option></select>` : `<a href="/">返回设备列表</a>`}
      <button type="button" id="local-help-button">使用说明</button></div>`;
    document.body.prepend(bar);
    document.documentElement.classList.add("local-edition");
    const select = bar.querySelector("select");
    if (select) {
      select.value = localStorage.getItem(profileKey) || "auto";
      select.addEventListener("change", () => { localStorage.setItem(profileKey, select.value); location.reload(); });
    }
    const dialog = document.createElement("dialog");
    dialog.className = "local-help";
    dialog.innerHTML = `<form method="dialog"><div class="local-dialog-head"><h2>星闪悦动 · 本地驱动</h2><button aria-label="关闭说明">×</button></div></form>
      <p>连接 USB 设备后，点击「添加设备」，在浏览器弹窗中选择并授权。VID/PID 与厂商品牌限制已移除。</p>
      <p>未知设备可在上方选择驱动协议。设备需要兼容星闪悦动的通信协议；Chrome 的受保护 HID 接口仍由浏览器管理。</p>
      <p>界面、驱动代码和设备目录均从本机读取。账号、云同步、社区和在线固件服务需要原站网络，本地版使用本地配置与固件文件功能。</p>
      <details><summary>自定义设备目录</summary><p>特殊鼠标芯片可导入包含目标地址的 JSON 设备目录。格式与 <a href="/local-data/device-catalog.json" target="_blank">本地设备目录</a>一致。设置仅保存在本机浏览器。</p>
      <label class="local-file-label">导入设备目录 <input type="file" id="local-catalog-input" accept="application/json,.json"></label>
      <button type="button" id="local-catalog-reset">清除自定义目录</button><p id="local-import-status" role="status"></p></details>`;
    document.body.append(dialog);
    fetch("/local/resource-status.json").then(r => r.json()).then(status => {
      if (status.missingScripts || status.missingStyles) {
        const warning = document.createElement("p");
        warning.className = "local-resource-warning";
        warning.textContent = "部分功能页面的资源尚未补齐，当前版本还不能作为完整离线驱动使用。原站资源服务器暂时拒绝连接。";
        dialog.querySelector("form").after(warning);
        bar.querySelector(".local-identity>span:last-child").textContent = "准入已开放 · 资源待补齐";
      }
    }).catch(() => {});
    bar.querySelector("#local-help-button").addEventListener("click", () => dialog.showModal());
    dialog.addEventListener("click", e => { if (e.target === dialog) dialog.close(); });
    dialog.querySelector("#local-catalog-input").addEventListener("change", async e => {
      const status = dialog.querySelector("#local-import-status");
      try {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 4 * 1024 * 1024) throw new Error("目录文件不能超过 4 MB");
        const { validateCatalog } = await import("./device-policy.mjs");
        const catalog = validateCatalog(JSON.parse(await file.text()));
        localStorage.setItem(catalogKey, JSON.stringify(catalog));
        status.textContent = `已导入 ${Object.keys(catalog).length} 个设备定义，重新连接设备后生效。`;
      } catch (error) { status.textContent = error.message; }
    });
    dialog.querySelector("#local-catalog-reset").addEventListener("click", () => {
      localStorage.removeItem(catalogKey);
      dialog.querySelector("#local-import-status").textContent = "自定义目录已清除。";
    });
  });
})();

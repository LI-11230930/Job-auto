function detectSiteFromUrl(url) {
  const low = (url || "").toLowerCase();
  if (low.includes("zhipin.com")) return "zhipin";
  if (low.includes("zhaopin.com")) return "zhaopin";
  if (low.includes("51job.com")) return "51job";
  if (low.includes("iguopin.com")) return "iguopin";
  if (low.includes("shixiseng.com")) return "shixiseng";
  if (low.includes("ncss.cn")) return "ncss";
  return "auto";
}

function sendBgMessage(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, (resp) => resolve(resp || { ok: false, error: "无响应" }));
  });
}

function clickNextPageInTab(site) {
  const selectorsBySite = {
    zhipin: [".options-pages a.next:not(.disabled)", "a i.ui-icon-arrow-right"],
    "51job": [".el-pagination button.btn-next:not([disabled])", "li.next:not(.disabled) a"],
    iguopin: [
      ".ant-pagination-next:not(.ant-pagination-disabled):not([aria-disabled='true']) button",
      "li[title='下一页'][aria-disabled='false'] button",
      ".ant-pagination-next:not(.ant-pagination-disabled):not([aria-disabled='true'])",
      ".el-pagination button.btn-next:not([disabled])",
    ],
    zhaopin: [".soupager a.btn:last-child", "button.btn-next:not([disabled])", ".el-pagination button.btn-next:not([disabled])"],
  };
  const candidates = selectorsBySite[site] || [
    ".ant-pagination-next:not(.ant-pagination-disabled):not([aria-disabled='true']) button",
    ".el-pagination button.btn-next:not([disabled])",
    "a.next:not(.disabled)",
  ];
  for (const sel of candidates) {
    const el = document.querySelector(sel);
    if (el && !el.closest(".ant-pagination-disabled, [aria-disabled='true']")) {
      const target = el.tagName === "I" && el.parentElement ? el.parentElement : el;
      target.scrollIntoView({ block: "center" });
      target.click();
      return true;
    }
  }
  return false;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function fillPortalFormInTab(profileData, pkgData) {
  const basic = (profileData && profileData.basic) || {};
  const edu = Array.isArray(profileData && profileData.education) && profileData.education[0] ? profileData.education[0] : {};
  const qaObj = (pkgData && pkgData.qa) || {};
  const introText =
    (pkgData && pkgData.greeting) ||
    qaObj.why_company ||
    qaObj.self_intro ||
    basic.workYears ||
    "";

  const rules = [
    { val: basic.name, re: /^(?!.*公司)(?!.*岗位).*?(姓名|真实姓名|full.?name|your.?name|name)/i },
    { val: basic.phone, re: /(手机|联系电话|手机号|移动电话|phone|mobile|tel)/i },
    { val: basic.email, re: /(邮箱|电子邮箱|email|e-mail)/i },
    { val: basic.birthday, re: /(出生日期|生日|birthday|birth)/i },
    { val: basic.gender, re: /(性别|gender)/i },
    { val: basic.politics, re: /(政治面貌|politic)/i },
    { val: basic.idNumber, re: /(身份证|证件号|id.?num)/i },
    { val: edu.school, re: /(毕业院校|学校名称|所在院校|院校|school|university|college)/i },
    { val: edu.major, re: /(专业名称|所学专业|专业|major)/i },
    { val: edu.degree, re: /(最高学历|学历|学位|degree|education)/i },
    { val: basic.address || basic.nativePlace, re: /(现居|居住地|期望城市|城市|通讯地址|city|address)/i },
    { val: introText, re: /(自我评价|自我介绍|个人优势|求职动机|补充说明|简介|intro|summary|motivation|advantage)/i, allowTextarea: true },
  ];

  const setNativeVal = (el, val) => {
    const proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) {
      desc.set.call(el, val);
    } else {
      el.value = val;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  let filled = 0;
  const fields = document.querySelectorAll("input, textarea");
  fields.forEach((el) => {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    if (["hidden", "password", "file", "checkbox", "radio", "submit", "button", "reset"].includes(type)) return;
    if (el.disabled || el.readOnly) return;
    if (el.offsetParent === null && getComputedStyle(el).position !== "fixed") return;
    if ((el.value || "").trim()) return;

    let labelTxt = "";
    if (el.id) {
      const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lbl) labelTxt += " " + lbl.textContent;
    }
    const row = el.closest(".el-form-item, .ant-form-item, tr, label, .form-group, .field-item");
    if (row) labelTxt += " " + (row.textContent || "").slice(0, 80);
    const hint = [labelTxt, el.placeholder, el.name, el.id, el.getAttribute("aria-label")].filter(Boolean).join(" ");

    for (const r of rules) {
      if (!r.val) continue;
      if (el.tagName === "TEXTAREA" && !r.allowTextarea && !/(评价|介绍|优势|动机|说明|intro|summary)/i.test(hint)) continue;
      if (r.re.test(hint)) {
        setNativeVal(el, String(r.val).trim());
        filled += 1;
        break;
      }
    }
  });
  return { filled, url: window.location.href };
}

document.addEventListener("DOMContentLoaded", async () => {
  const healthBadge = document.getElementById("healthBadge");
  const siteNameEl = document.getElementById("siteName");
  const dbCountEl = document.getElementById("dbCount");
  const statusBox = document.getElementById("statusBox");
  const btnAutoScroll = document.getElementById("btnAutoScroll");
  const btnStopScroll = document.getElementById("btnStopScroll");
  const btnAutoPage = document.getElementById("btnAutoPage");
  const btnOne = document.getElementById("btnOne");
  const autofillProfileSel = document.getElementById("autofillProfileSel");
  const autofillPkgSel = document.getElementById("autofillPkgSel");
  const btnAutofillPage = document.getElementById("btnAutofillPage");
  const btnCopyGreeting = document.getElementById("btnCopyGreeting");
  let autofillBundle = { profiles: [], packages: [] };

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const detectedSite = detectSiteFromUrl(tab?.url || "");
  siteNameEl.textContent = `${detectedSite} (${tab?.url ? new URL(tab.url).hostname : "-"})`;

  let serviceReady = false;
  const health = await sendBgMessage({ type: "CHECK_HEALTH" });
  if (health.ok) {
    serviceReady = true;
    const portLabel = (health.baseUrl || "").includes("8765") ? "8765" : "8788";
    healthBadge.textContent = `已连接 ${portLabel}`;
    healthBadge.className = "badge ok";
    dbCountEl.textContent = String(health.data?.total_in_db ?? "-");
    try {
      const bundleResp = await sendBgMessage({ type: "GET_AUTOFILL_BUNDLE" });
      if (bundleResp.ok && bundleResp.data) {
        autofillBundle = bundleResp.data;
        autofillProfileSel.replaceChildren();
        (autofillBundle.profiles || []).forEach((prof, idx) => {
          const opt = document.createElement("option");
          opt.value = String(idx);
          opt.textContent = prof.name || prof.id || `档案 ${idx + 1}`;
          autofillProfileSel.appendChild(opt);
        });
        if (!(autofillBundle.profiles || []).length) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "未发现档案，请先在设置导入简历";
          autofillProfileSel.appendChild(opt);
        }
        autofillPkgSel.replaceChildren();
        const emptyOpt = document.createElement("option");
        emptyOpt.value = "";
        emptyOpt.textContent = "仅填基础档案（不绑定特定岗位话术）";
        autofillPkgSel.appendChild(emptyOpt);
        (autofillBundle.packages || []).forEach((pkg, idx) => {
          const opt = document.createElement("option");
          opt.value = String(idx);
          opt.textContent = `${pkg.company} · ${pkg.title} (${pkg.score}分)`;
          autofillPkgSel.appendChild(opt);
        });
        btnAutofillPage.disabled = !(autofillBundle.profiles || []).length;
        btnCopyGreeting.disabled = !(autofillBundle.packages || []).length;
      }
    } catch (_) {
      // Do not block collection buttons if autofill bundle fails to load
    }
  } else {
    healthBadge.textContent = "未启动服务";
    healthBadge.className = "badge err";
    statusBox.textContent = "未检测到本地服务：请先双击根目录 start.bat（或运行 job-agent up），再点扩展图标重试。";
  }

  function syncUiState(st) {
    const running = Boolean(st?.running);
    btnAutoScroll.disabled = !serviceReady || running;
    btnAutoPage.disabled = !serviceReady || running;
    btnOne.disabled = !serviceReady || running;
    btnStopScroll.style.display = running ? "block" : "none";
    if (st?.message && (running || st?.lastResult)) {
      statusBox.textContent = st.message;
    }
    if (st?.lastResult?.total_in_db != null) {
      dbCountEl.textContent = String(st.lastResult.total_in_db);
    }
  }

  const initStateResp = await sendBgMessage({ type: "GET_STATE" });
  syncUiState(initStateResp.state);

  const pollTimer = setInterval(async () => {
    const resp = await sendBgMessage({ type: "GET_STATE" });
    if (resp.ok) {
      syncUiState(resp.state);
    }
  }, 700);
  window.addEventListener("unload", () => clearInterval(pollTimer));

  btnAutoScroll.addEventListener("click", async () => {
    const resp = await sendBgMessage({
      type: "START_AUTO_SCROLL",
      tabId: tab.id,
      site: detectedSite,
      maxRounds: 30,
    });
    if (!resp.ok) {
      statusBox.textContent = resp.error || "启动下拉采集失败";
      return;
    }
    const st = await sendBgMessage({ type: "GET_STATE" });
    syncUiState(st.state);
  });

  btnStopScroll.addEventListener("click", async () => {
    await sendBgMessage({ type: "STOP_AUTO_SCROLL" });
    statusBox.textContent = "正在通知后台停止下拉并写入已加载岗位...";
  });

  btnOne.addEventListener("click", async () => {
    btnOne.disabled = true;
    btnAutoPage.disabled = true;
    btnAutoScroll.disabled = true;
    statusBox.textContent = "正在采集当前页并写入本地数据库...";
    try {
      const resp = await sendBgMessage({
        type: "CAPTURE_ONCE_NOW",
        tabId: tab.id,
        site: detectedSite,
      });
      if (!resp.ok) throw new Error(resp.error || "采集失败");
      if (resp.gated) {
        statusBox.textContent = "检测到登录或验证提示，已安全停止。请手动完成后重试。";
      } else {
        const d = resp.data;
        dbCountEl.textContent = String(d.total_in_db ?? "-");
        statusBox.textContent = `采集成功 [${d.site}]：解析 ${d.extracted} 条，新增 ${d.inserted} 条，更新 ${d.updated} 条。\n库内总计：${d.total_in_db} 条。`;
      }
    } catch (e) {
      statusBox.textContent = `采集失败：${e.message || e}`;
    } finally {
      btnOne.disabled = !serviceReady;
      btnAutoPage.disabled = !serviceReady;
      btnAutoScroll.disabled = !serviceReady;
    }
  });

  btnAutoPage.addEventListener("click", async () => {
    btnOne.disabled = true;
    btnAutoPage.disabled = true;
    btnAutoScroll.disabled = true;
    let totalIns = 0;
    let totalExt = 0;
    try {
      for (let i = 1; i <= 3; i += 1) {
        statusBox.textContent = `正在采集第 ${i}/3 页...`;
        const resp = await sendBgMessage({
          type: "CAPTURE_ONCE_NOW",
          tabId: tab.id,
          site: detectedSite,
        });
        if (!resp.ok) throw new Error(resp.error || "采集失败");
        if (resp.gated) {
          statusBox.textContent = `第 ${i} 页遇到验证/登录弹窗，已安全停止。累计新增 ${totalIns} 条。`;
          break;
        }
        const d = resp.data;
        totalExt += d.extracted || 0;
        totalIns += d.inserted || 0;
        dbCountEl.textContent = String(d.total_in_db ?? "-");
        if (i === 3) {
          statusBox.textContent = `完成 3 页低频采集：累计解析 ${totalExt} 条，新增 ${totalIns} 条，库内总计 ${d.total_in_db} 条。`;
          break;
        }
        const nextRes = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: clickNextPageInTab,
          args: [detectedSite],
        });
        if (!nextRes?.[0]?.result) {
          statusBox.textContent = `已到达末页（共 ${i} 页）：累计解析 ${totalExt} 条，新增 ${totalIns} 条，库内总计 ${d.total_in_db} 条。`;
          break;
        }
        const waitMs = 5000 + Math.floor(Math.random() * 1500);
        statusBox.textContent = `第 ${i} 页已入库（累计新增 ${totalIns} 条），等待 ${(waitMs / 1000).toFixed(1)} 秒后采集下一页...`;
        await sleep(waitMs);
      }
    } catch (e) {
      statusBox.textContent = `翻页采集异常：${e.message || e}`;
    } finally {
      btnOne.disabled = !serviceReady;
      btnAutoPage.disabled = !serviceReady;
      btnAutoScroll.disabled = !serviceReady;
    }
  });

  btnAutofillPage.addEventListener("click", async () => {
    const profIdx = Number(autofillProfileSel.value);
    const profObj = (autofillBundle.profiles || [])[profIdx];
    if (!profObj || !profObj.data) {
      statusBox.textContent = "请先在设置页导入简历并同步档案。";
      return;
    }
    const pkgIdxStr = autofillPkgSel.value;
    const pkgObj = pkgIdxStr !== "" ? (autofillBundle.packages || [])[Number(pkgIdxStr)] : null;
    try {
      const exec = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: fillPortalFormInTab,
        args: [profObj.data, pkgObj],
      });
      const r = exec?.[0]?.result || { filled: 0 };
      statusBox.textContent = `网申智能回填完成（严格只填不提交）：共填充 ${r.filled} 个表单字段，请核对后再手动提交。`;
    } catch (e) {
      statusBox.textContent = `当前页面不支持脚本回填：${e.message || e}`;
    }
  });

  btnCopyGreeting.addEventListener("click", async () => {
    const pkgIdx = Number(autofillPkgSel.value || 0);
    const pkgObj = (autofillBundle.packages || [])[pkgIdx];
    const txt = (pkgObj && pkgObj.greeting) || "";
    if (!txt) {
      statusBox.textContent = "该岗位暂无生成打招呼话术，请先选中有话术的岗位。";
      return;
    }
    await navigator.clipboard.writeText(txt);
    statusBox.textContent = `已复制「${pkgObj.company} · ${pkgObj.title}」专属打招呼话术到剪贴板！`;
  });
});

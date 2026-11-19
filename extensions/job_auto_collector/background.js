const BASE_URLS = ["http://127.0.0.1:8788", "http://127.0.0.1:8765"];
let activeBaseUrl = BASE_URLS[0];

let taskState = {
  running: false,
  stopRequested: false,
  tabId: null,
  site: "auto",
  round: 0,
  cardCount: 0,
  message: "就绪：打开搜索结果页后点击「自动下拉到底并采集」。",
  lastResult: null,
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function setBadge(text, color) {
  try {
    chrome.action.setBadgeText({ text: String(text || "") });
    if (color) {
      chrome.action.setBadgeBackgroundColor({ color });
    }
  } catch (_) {
    // ignore badge errors
  }
}

function pageScrollStepAndProbe() {
  const headText = (document.body ? document.body.innerText : "").slice(0, 3500);
  const url = window.location.href || "";
  const gated =
    /login|passport|verify|captcha/i.test(url) ||
    ["滑动验证", "安全验证", "请完成验证", "行为验证", "扫码登录", "请先登录"].some((m) =>
      headText.includes(m)
    );

  // Scroll window and any scrollable job list containers politely
  const step = Math.max(500, Math.round(window.innerHeight * 0.85));
  window.scrollBy({ top: step, behavior: "smooth" });
  const containers = document.querySelectorAll(
    ".job-list-box, .job-list-wrapper, .position-list, .el-scrollbar__wrap, main"
  );
  containers.forEach((c) => {
    if (c && c.scrollHeight > c.clientHeight + 40) {
      c.scrollTop = Math.min(c.scrollHeight, c.scrollTop + step);
    }
  });

  const maxContainerHeight = Array.from(containers).reduce(
    (mx, el) => Math.max(mx, el ? el.scrollHeight : 0),
    0
  );
  const scrollHeight = Math.max(
    document.documentElement ? document.documentElement.scrollHeight : 0,
    document.body ? document.body.scrollHeight : 0,
    maxContainerHeight
  );
  const cardCount = document.querySelectorAll(
    ".job-card-wrapper, li.job-card-box, .position-list__item, .position-card, .joblist-box__item, .joblist-item, .j_joblist .e, .job-card, [data-intern-id]"
  ).length;

  return { gated, scrollHeight, cardCount };
}

function pageExtractAll(site) {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const url = window.location.href;
  const html = document.documentElement ? document.documentElement.outerHTML : "";
  const headText = (document.body ? document.body.innerText : "").slice(0, 3500);
  const gated =
    /login|passport|verify|captcha/i.test(url) ||
    ["滑动验证", "安全验证", "请完成验证", "行为验证", "扫码登录", "请先登录"].some((m) =>
      headText.includes(m)
    );

  const cards = [];
  if (site === "zhipin" || url.includes("zhipin.com")) {
    document.querySelectorAll(".job-card-wrapper, li.job-card-box").forEach((el) => {
      const a = el.querySelector('a.job-name, a.job-title, a[href*="job_detail"]');
      const title = clean(a?.textContent || el.querySelector(".job-name")?.textContent);
      const company = clean(
        el.querySelector(".company-name a, .company-name, .boss-name")?.textContent
      );
      const city = clean(el.querySelector(".job-area, .company-location")?.textContent);
      const salary = clean(el.querySelector(".salary, .job-salary")?.textContent);
      const tags = Array.from(el.querySelectorAll(".tag-list li, .job-tag, ul li"))
        .map((t) => clean(t.textContent))
        .filter(Boolean)
        .slice(0, 8);
      if (title && company) {
        cards.push({ title, company, city, salary, tags, url: a?.href || url });
      }
    });
  } else if (site === "zhaopin" || url.includes("zhaopin.com")) {
    document.querySelectorAll(".position-list__item, .position-card").forEach((el) => {
      const card = el.classList.contains("position-card")
        ? el
        : el.querySelector(".position-card") || el;
      const title = clean(card.querySelector(".position-card__job-name")?.textContent);
      const company = clean(card.querySelector(".position-card__company__name")?.textContent);
      const city = clean(card.querySelector(".position-card__city-name")?.textContent).replace(
        /[「」\[\]()]/g,
        ""
      );
      const salary = clean(card.querySelector(".position-card__salary")?.textContent);
      const tags = Array.from(card.querySelectorAll(".position-card__tags__item"))
        .map((t) => clean(t.textContent))
        .filter(Boolean)
        .slice(0, 8);
      let jobUrl = "";
      try {
        const rawOpt = card.getAttribute("data-sensors-exposure-option") || "";
        const jdnoMatch = rawOpt.match(/"jdno"\s*:\s*"([A-Za-z0-9_]+)"/);
        if (jdnoMatch) jobUrl = `https://jobs.zhaopin.com/${jdnoMatch[1]}.htm`;
      } catch (_) {
        jobUrl = "";
      }
      if (title && company) {
        cards.push({ title, company, city, salary, tags, url: jobUrl || url });
      }
    });
    if (cards.length === 0) {
      document.querySelectorAll(".joblist-box__item, .positionlist__item").forEach((el) => {
        const title = clean(el.querySelector(".jobinfo__name, a[class*='job']")?.textContent);
        const company = clean(
          el.querySelector(".companyinfo__name, a[class*='company']")?.textContent
        );
        const infoItems = Array.from(el.querySelectorAll(".jobinfo__other-info-item")).map((x) =>
          clean(x.textContent)
        );
        const city = infoItems[0] || "";
        const salary = clean(el.querySelector(".jobinfo__salary")?.textContent);
        const a = el.querySelector("a.jobinfo__name, a[href*='zhaopin.com']");
        if (title && company) {
          cards.push({
            title,
            company,
            city,
            salary,
            tags: infoItems.slice(1, 6),
            url: a?.href || url,
          });
        }
      });
    }
  } else if (site === "51job" || url.includes("51job.com")) {
    document.querySelectorAll(".joblist-item, .j_joblist .e").forEach((el) => {
      const title = clean(el.querySelector(".jname, .job-name")?.textContent);
      const company = clean(el.querySelector(".cname, .comp-name")?.textContent);
      const city = clean(el.querySelector(".area, .d.at")?.textContent);
      const salary = clean(el.querySelector(".sal, .salary")?.textContent);
      const a = el.querySelector('a[href*="51job.com"]');
      if (title && company) {
        cards.push({ title, company, city, salary, tags: [], url: a?.href || url });
      }
    });
  } else if (site === "iguopin" || url.includes("iguopin.com")) {
    document.querySelectorAll(".job-card").forEach((el) => {
      const title = clean(
        (
          el.querySelector(".job-name") ||
          el.querySelector('[class*="job-name"]') ||
          el.querySelector('[class*="title"], h3, h4')
        )?.textContent
      );
      const company = clean(
        el.querySelector(
          'a.company-name, .company-name, .department-name, [class*="company"], [class*="corp"], [class*="org"]'
        )?.textContent
      );
      const city = clean(
        el.querySelector('.job-district, [class*="district"], [class*="city"], [class*="area"], [class*="location"]')
          ?.textContent
      ).replace(/[「」\[\]()]/g, "");
      const salary = clean(el.querySelector('.job-salary, [class*="salary"]')?.textContent);
      const tags = Array.from(
        el.querySelectorAll(".job-info .tag-item, .job-tag .ant-tag, .company-info .company-info-item")
      )
        .map((t) => clean(t.textContent))
        .filter(Boolean)
        .slice(0, 8);
      const trackerId = clean(el.getAttribute("data-tracker"));
      const a = el.querySelector('a[href*="/job/detail"]');
      const jobUrl = a?.href || (trackerId ? `https://www.iguopin.com/job/detail?id=${trackerId}` : url);
      if (title && company) {
        cards.push({ title, company, city, salary, tags, url: jobUrl });
      }
    });
    if (cards.length === 0) {
      document.querySelectorAll('a[href*="/job/detail/"]').forEach((a) => {
        const card = a.closest('div[class*="item"], li, .el-card') || a.parentElement?.parentElement;
        if (!card) return;
        const title = clean(
          card.querySelector('[class*="job-name"], [class*="title"], h3, h4')?.textContent ||
            a.textContent
        );
        const company = clean(
          card.querySelector('[class*="company"], [class*="corp"], [class*="org"]')?.textContent
        );
        const city = clean(
          card.querySelector('[class*="city"], [class*="area"], [class*="location"]')?.textContent
        ).replace(/[「」\[\]()]/g, "");
        if (title && company) {
          cards.push({ title, company, city, salary: "", tags: [], url: a.href || url });
        }
      });
    }
  } else if (site === "shixiseng" || url.includes("shixiseng.com")) {
    document.querySelectorAll(".intern-wrap, [data-intern-id]").forEach((el) => {
      const a = el.querySelector("a.title, a[href*='/intern/']");
      const title = clean(a?.textContent);
      const company = clean(el.querySelector("a[href*='/com/'], .company-name")?.textContent);
      const city = clean(el.querySelector(".city-ellipsis, .city")?.textContent);
      if (title && company) {
        cards.push({ title, company, city, salary: "", tags: ["实习"], url: a?.href || url });
      }
    });
  }

  return { url, html, cards, gated };
}

async function resolveActiveBaseUrl() {
  for (const base of BASE_URLS) {
    try {
      const res = await fetch(`${base}/api/health`);
      if (res.ok) {
        activeBaseUrl = base;
        return { base, data: await res.json() };
      }
    } catch (_) {
      // try next candidate port
    }
  }
  throw new Error("未连接本地服务（8788 统一工作台或 8765 接收器）");
}

async function postToInbox(payload) {
  let targetBase = activeBaseUrl;
  try {
    const check = await resolveActiveBaseUrl();
    targetBase = check.base;
  } catch (_) {
    // keep activeBaseUrl fallback
  }
  const res = await fetch(`${targetBase}/api/ingest-page`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function fetchAutofillBundle() {
  let targetBase = activeBaseUrl;
  try {
    const check = await resolveActiveBaseUrl();
    targetBase = check.base;
  } catch (_) {
    // keep activeBaseUrl fallback
  }
  const res = await fetch(`${targetBase}/api/autofill/bundle`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function runAutoScrollLoop(tabId, site, maxRounds = 30) {
  taskState = {
    running: true,
    stopRequested: false,
    tabId,
    site,
    round: 0,
    cardCount: 0,
    message: "正在自动下拉加载更多岗位，您可保持页面打开无需手动滚动...",
    lastResult: null,
  };
  setBadge("...", "#d97706");

  let lastHeight = 0;
  let lastCount = 0;
  let stagnant = 0;
  let stoppedReason = "已下拉到底部（无更多新岗位）";

  try {
    for (let i = 1; i <= maxRounds; i += 1) {
      if (taskState.stopRequested) {
        stoppedReason = "已按您的指令提前停止下拉";
        break;
      }
      const exec = await chrome.scripting.executeScript({
        target: { tabId },
        func: pageScrollStepAndProbe,
      });
      const probe = exec?.[0]?.result;
      if (!probe) {
        stoppedReason = "无法读取标签页，尝试保存当前内容";
        break;
      }
      if (probe.gated) {
        setBadge("GATE", "#dc2626");
        stoppedReason = "检测到登录或验证提示，已安全停止并尝试保存已加载数据";
        break;
      }

      taskState.round = i;
      taskState.cardCount = probe.cardCount;
      if (probe.scrollHeight <= lastHeight + 20 && probe.cardCount <= lastCount) {
        stagnant += 1;
      } else {
        stagnant = 0;
        lastHeight = probe.scrollHeight;
        lastCount = probe.cardCount;
      }

      taskState.message = `自动下拉第 ${i}/${maxRounds} 次 · 已识别约 ${probe.cardCount} 张卡片（连续无新增 ${stagnant}/3）`;
      if (stagnant >= 3) {
        stoppedReason = `连续 3 次下拉无新增（约 ${probe.cardCount} 张卡片），已到达底部`;
        break;
      }
      await sleep(1700 + Math.floor(Math.random() * 700));
    }

    taskState.message = `${stoppedReason}，正在统一解析并写入本地数据库...`;
    const cap = await chrome.scripting.executeScript({
      target: { tabId },
      func: pageExtractAll,
      args: [site],
    });
    const data = cap?.[0]?.result;
    if (!data) throw new Error("抓取页面内容失败");

    const resp = await postToInbox({
      url: data.url,
      site,
      html: data.html,
      cards: data.cards,
      exclude_social: true,
    });
    taskState.lastResult = resp;
    taskState.message = `${stoppedReason}。\n入库完成 [${resp.site}]：解析 ${resp.extracted} 条，新增 ${resp.inserted} 条，更新 ${resp.updated} 条（总计 ${resp.total_in_db} 条）。`;
    setBadge(`+${resp.inserted}`, "#16a34a");
  } catch (err) {
    taskState.message = `自动下拉采集出错：${err?.message || err}`;
    setBadge("ERR", "#dc2626");
  } finally {
    taskState.running = false;
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || typeof msg !== "object") return false;

  if (msg.type === "CHECK_HEALTH") {
    resolveActiveBaseUrl()
      .then(({ base, data }) => sendResponse({ ok: true, baseUrl: base, data }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "GET_STATE") {
    sendResponse({ ok: true, state: taskState });
    return false;
  }

  if (msg.type === "STOP_AUTO_SCROLL") {
    taskState.stopRequested = true;
    sendResponse({ ok: true });
    return false;
  }

  if (msg.type === "START_AUTO_SCROLL") {
    if (taskState.running) {
      sendResponse({ ok: false, error: "后台已在下拉采集中" });
      return false;
    }
    runAutoScrollLoop(msg.tabId, msg.site, msg.maxRounds || 30);
    sendResponse({ ok: true });
    return false;
  }

  if (msg.type === "CAPTURE_ONCE_NOW") {
    chrome.scripting
      .executeScript({
        target: { tabId: msg.tabId },
        func: pageExtractAll,
        args: [msg.site],
      })
      .then(async (exec) => {
        const data = exec?.[0]?.result;
        if (!data) throw new Error("无法读取页面 DOM");
        if (data.gated) {
          sendResponse({ ok: true, gated: true });
          return;
        }
        const resp = await postToInbox({
          url: data.url,
          site: msg.site,
          html: data.html,
          cards: data.cards,
          exclude_social: true,
        });
        setBadge(`+${resp.inserted}`, "#16a34a");
        sendResponse({ ok: true, gated: false, data: resp });
      })
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "INGEST_PAGE") {
    postToInbox(msg.payload)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "GET_AUTOFILL_BUNDLE") {
    fetchAutofillBundle()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  return false;
});

/**
 * Job-auto Zero-Knowledge Cloud Relay (Cloudflare Worker + KV)
 *
 * Security model:
 * - Zero knowledge: plaintext resume/job data & encryption passphrase NEVER reach this Worker.
 * - Worker only stores AES-256-GCM ciphertext envelopes (`batch:<pairing_id>`, `actions:<pairing_id>`)
 *   with automatic TTL expiry (`ttl_days`, default 7 days).
 * - `/mobile` serves the standalone WebCrypto client so phones decrypt locally in memory over HTTPS.
 *
 * Required Worker binding:
 * - KV Namespace binding name: `RELAY_KV`
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const MAX_BODY_BYTES = 512 * 1024;

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...CORS_HEADERS,
    },
  });
}

function cleanPairingId(raw) {
  const pid = String(raw || "").trim();
  if (!pid || pid.length > 96 || !/^[a-zA-Z0-9._-]+$/.test(pid)) {
    return "";
  }
  return pid;
}

function resolveTtlSeconds(ttlDays) {
  const days = Number(ttlDays);
  const clamped = Number.isFinite(days) ? Math.min(Math.max(Math.round(days), 1), 30) : 7;
  return clamped * 86400;
}

function renderMobileHtml() {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1" />
  <title>Job-auto · 零知识手机加密审阅端</title>
  <style>
    :root { --bg:#f9f8fe; --card:#fff; --accent:#7c3aed; --ink:#1e1b4b; --muted:#6b7280; --line:#e9d5ff; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei UI",sans-serif; background:var(--bg); color:var(--ink); padding:14px; }
    .wrap { max-width:680px; margin:0 auto; }
    .hdr { background:linear-gradient(135deg,#2e1065,#4c1d95); color:#fff; border-radius:14px; padding:16px; margin-bottom:12px; }
    .hdr h1 { margin:0 0 4px; font-size:17px; }
    .hdr p { margin:0; font-size:12px; opacity:.88; line-height:1.5; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; margin-bottom:12px; }
    .lbl { display:block; font-size:12px; font-weight:700; margin-bottom:4px; color:#374151; }
    .inp { width:100%; padding:9px 10px; border:1px solid #d8b4fe; border-radius:8px; font-size:13px; margin-bottom:10px; font-family:inherit; }
    .row2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    @media (max-width:520px) { .row2 { grid-template-columns:1fr; } }
    .btn { border:1px solid var(--line); background:#fff; color:var(--ink); padding:8px 12px; border-radius:9px; font-size:13px; font-weight:700; cursor:pointer; }
    .btn-primary { background:var(--accent); color:#fff; border-color:var(--accent); }
    .btn-ok { background:#0f766e; color:#fff; border-color:#0f766e; }
    .btn-warn { background:#d97706; color:#fff; border-color:#d97706; }
    .btn-bad { background:#dc2626; color:#fff; border-color:#dc2626; }
    .pill { display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; background:#ede9fe; color:#5b21b6; margin-right:6px; }
    .job-title { font-size:15.5px; font-weight:800; margin:6px 0 4px; }
    .meta { font-size:12px; color:var(--muted); margin-bottom:8px; }
    .acts { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .st { font-size:12.5px; padding:8px 10px; border-radius:8px; background:#f3f0ff; color:#4c1d95; margin-bottom:10px; display:none; }
    .st.show { display:block; }
  </style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>🔒 Job-auto 零知识加密审阅端</h1>
    <p>AES-256-GCM 加解密全部在本机浏览器内存中完成；中转服务器仅保存密文乱码，不触碰口令与简历。</p>
  </div>
  <div class="card">
    <div class="row2">
      <div>
        <label class="lbl" for="pid">设备配对 ID（pairing_id）</label>
        <input id="pid" class="inp" placeholder="与桌面端设置一致的配对 ID" />
      </div>
      <div>
        <label class="lbl" for="sec">端到端加密口令（不上传服务器）</label>
        <input id="sec" type="password" class="inp" placeholder="与桌面端一致的配对口令..." />
      </div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn btn-primary" id="btnPull">⬇️ 拉取并本地解密待审岗位</button>
      <button class="btn" id="btnFlush" style="display:none;">⬆️ 提交已选审批结果回云端 (<span id="actCnt">0</span>)</button>
    </div>
  </div>
  <div id="statusMsg" class="st"></div>
  <div id="jobsList"></div>
</div>
<script>
(() => {
  const el = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  const b64uToBytes = (str) => {
    const pad = '='.repeat((4 - (str.length % 4)) % 4);
    const bin = atob((str + pad).replace(/-/g, '+').replace(/_/g, '/'));
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  };
  const bytesToB64u = (bytes) => {
    let bin = '';
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/g, '');
  };
  async function deriveAesKey(secret) {
    const raw = new TextEncoder().encode((secret || '').trim());
    if (!raw.length) throw new Error('请先输入端到端加密口令');
    const digest = await crypto.subtle.digest('SHA-256', raw);
    return crypto.subtle.importKey('raw', digest, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
  }
  async function openEnvelope(envelope, secret) {
    if (!envelope || envelope.alg !== 'AES-256-GCM') throw new Error('无效密文格式');
    const key = await deriveAesKey(secret);
    const iv = b64uToBytes(String(envelope.nonce || ''));
    const ct = b64uToBytes(String(envelope.ciphertext || ''));
    const pid = String(envelope.pairing_id || '');
    const params = { name: 'AES-GCM', iv, tagLength: 128 };
    if (pid) params.additionalData = new TextEncoder().encode(pid);
    const plain = await crypto.subtle.decrypt(params, key, ct);
    return JSON.parse(new TextDecoder().decode(plain));
  }
  async function sealEnvelope(data, secret, pairingId) {
    const key = await deriveAesKey(secret);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plain = new TextEncoder().encode(JSON.stringify(data));
    const params = { name: 'AES-GCM', iv, tagLength: 128 };
    if (pairingId) params.additionalData = new TextEncoder().encode(pairingId);
    const ctBuf = await crypto.subtle.encrypt(params, key, plain);
    return {
      v: 1, alg: 'AES-256-GCM', pairing_id: pairingId,
      created_at: new Date().toISOString(),
      nonce: bytesToB64u(iv), ciphertext: bytesToB64u(new Uint8Array(ctBuf)),
    };
  }
  const qsPid = new URLSearchParams(window.location.search).get('pairing_id');
  if (qsPid) el('pid').value = qsPid;
  const pendingActions = new Map();
  let itemsCache = [];
  const DEC_LABEL = { approved: '通过入队列', later: '暂缓', rejected: '不考虑' };
  const showStatus = (msg) => { const b = el('statusMsg'); b.textContent = msg; b.classList.add('show'); };
  const updateActionBtn = () => { el('actCnt').textContent = String(pendingActions.size); el('btnFlush').style.display = pendingActions.size > 0 ? 'inline-block' : 'none'; };
  function renderJobs() {
    const box = el('jobsList');
    box.replaceChildren();
    if (!itemsCache.length) {
      const d = document.createElement('div'); d.className = 'card'; d.style.color = '#6b7280';
      d.textContent = '当前配对 ID 暂无云端密文批次，请先在桌面 App 点击「立即加密推送到云端」。';
      box.appendChild(d); return;
    }
    itemsCache.forEach((p) => {
      const pid = p.package_id || p.id;
      const picked = pendingActions.get(pid)?.decision || '';
      const safeUrl = (p.url || '').match(/^https?:\\/\\//i) ? esc(p.url) : '';
      const card = document.createElement('div'); card.className = 'card';
      card.innerHTML =
        '<div><span class="pill">' + esc(p.score ?? '--') + ' 分</span><span class="pill">' + esc(p.job_type || '校招') + '</span>' +
        (p.deadline ? '<span class="pill">截止 ' + esc(p.deadline) + '</span>' : '') +
        (picked ? '<span class="pill" style="background:#dcfce7;color:#166534;">已选: ' + esc(DEC_LABEL[picked] || picked) + '</span>' : '') + '</div>' +
        '<div class="job-title">' + esc(p.company || '') + ' · ' + esc(p.title || '') + '</div>' +
        '<div class="meta">' + esc((p.cities || []).join('/') || '城市未标注') + ' · 来源 ' + esc(p.source || '-') + (safeUrl ? ' · <a href="' + safeUrl + '" target="_blank" rel="noopener">原岗位</a>' : '') + '</div>' +
        ((p.reasons || []).length ? '<div style="font-size:12.5px;line-height:1.5;margin-bottom:6px;">匹配亮点：' + esc(p.reasons.join('；')) + '</div>' : '') +
        ((p.gaps || []).length ? '<div style="font-size:12px;color:#b45309;margin-bottom:6px;">短板提示：' + esc(p.gaps.join('；')) + '</div>' : '');
      const acts = document.createElement('div'); acts.className = 'acts';
      [['approved', '通过入队列', 'btn-ok'], ['later', '暂缓', 'btn-warn'], ['rejected', '不考虑', 'btn-bad']].forEach(([act, label, cls]) => {
        const b = document.createElement('button'); b.className = 'btn ' + cls; b.textContent = label;
        b.onclick = () => { pendingActions.set(pid, { package_id: pid, decision: act, reason: 'mobile_relay_' + act }); updateActionBtn(); renderJobs(); };
        acts.appendChild(b);
      });
      card.appendChild(acts); box.appendChild(card);
    });
  }
  el('btnPull').addEventListener('click', async () => {
    try {
      const pairingId = (el('pid').value || '').trim();
      const secret = el('sec').value || '';
      if (!pairingId) throw new Error('请输入设备配对 ID');
      showStatus('正在拉取并尝试本地解密...');
      const resp = await fetch(window.location.origin + '/pull-batch?pairing_id=' + encodeURIComponent(pairingId));
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      if (!data.envelope) { itemsCache = []; renderJobs(); showStatus('云端当前没有该配对 ID 的待审密文批次。'); return; }
      const opened = await openEnvelope(data.envelope, secret);
      itemsCache = opened.items || []; renderJobs();
      showStatus('✅ 本地解密成功：共 ' + itemsCache.length + ' 条待审岗位（生成于 ' + (opened.generated_at || '-') + '）。');
    } catch (err) {
      showStatus('❌ 拉取或解密失败：' + (err.message || err));
    }
  });
  el('btnFlush').addEventListener('click', async () => {
    try {
      const pairingId = (el('pid').value || '').trim();
      const secret = el('sec').value || '';
      const actions = Array.from(pendingActions.values());
      const envelope = await sealEnvelope({ actions, submitted_at: new Date().toISOString() }, secret, pairingId);
      const resp = await fetch(window.location.origin + '/ack-actions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ envelope }),
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      showStatus('✅ 已加密回传 ' + actions.length + ' 条审批决定，回桌面 App 点「拉取手机端审批结果」即可同步入列！');
      pendingActions.clear(); updateActionBtn(); renderJobs();
    } catch (err) {
      showStatus('❌ 提交失败：' + (err.message || err));
    }
  });
})();
</script>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "GET" && (path === "/health" || (path === "/" && !(request.headers.get("accept") || "").includes("text/html")))) {
      return jsonResponse({
        status: "ok",
        provider: "cloudflare_worker_kv",
        service: "job-auto-relay",
        kv_bound: Boolean(env && env.RELAY_KV),
      });
    }

    if (request.method === "GET" && (path === "/mobile" || path === "/")) {
      return new Response(renderMobileHtml(), {
        status: 200,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
        },
      });
    }

    if (!env || !env.RELAY_KV) {
      return jsonResponse({ status: "error", error: "Missing RELAY_KV namespace binding" }, 500);
    }

    if (request.method === "POST" && path === "/push-batch") {
      const raw = await request.text();
      if (raw.length > MAX_BODY_BYTES) {
        return jsonResponse({ status: "error", error: "Envelope exceeds 512KB limit" }, 413);
      }
      const body = JSON.parse(raw || "{}");
      const envelope = body.envelope;
      const pid = cleanPairingId(envelope && envelope.pairing_id);
      if (!pid || !envelope || envelope.alg !== "AES-256-GCM" || !envelope.ciphertext) {
        return jsonResponse({ status: "error", error: "Invalid AES-256-GCM envelope or pairing_id" }, 400);
      }
      const ttl = resolveTtlSeconds(body.ttl_days);
      await env.RELAY_KV.put(`batch:${pid}`, JSON.stringify(envelope), { expirationTtl: ttl });
      return jsonResponse({ status: "ok", pairing_id: pid, ttl_seconds: ttl });
    }

    if (request.method === "GET" && path === "/pull-batch") {
      const pid = cleanPairingId(url.searchParams.get("pairing_id"));
      if (!pid) return jsonResponse({ status: "error", error: "Invalid pairing_id" }, 400);
      const envelope = await env.RELAY_KV.get(`batch:${pid}`, { type: "json" });
      if (!envelope) return jsonResponse({ status: "empty", envelope: null });
      return jsonResponse({ status: "ok", envelope });
    }

    if (request.method === "POST" && path === "/ack-actions") {
      const raw = await request.text();
      if (raw.length > MAX_BODY_BYTES) {
        return jsonResponse({ status: "error", error: "Envelope exceeds 512KB limit" }, 413);
      }
      const body = JSON.parse(raw || "{}");
      const envelope = body.envelope;
      const pid = cleanPairingId(envelope && envelope.pairing_id);
      if (!pid || !envelope || envelope.alg !== "AES-256-GCM" || !envelope.ciphertext) {
        return jsonResponse({ status: "error", error: "Invalid AES-256-GCM envelope or pairing_id" }, 400);
      }
      const existing = (await env.RELAY_KV.get(`actions:${pid}`, { type: "json" })) || [];
      const queue = Array.isArray(existing) ? existing.slice(-19) : [existing];
      queue.push(envelope);
      await env.RELAY_KV.put(`actions:${pid}`, JSON.stringify(queue), { expirationTtl: 7 * 86400 });
      return jsonResponse({ status: "ok", pairing_id: pid, queued: queue.length });
    }

    if (request.method === "GET" && path === "/pull-actions") {
      const pid = cleanPairingId(url.searchParams.get("pairing_id"));
      if (!pid) return jsonResponse({ status: "error", error: "Invalid pairing_id" }, 400);
      const stored = await env.RELAY_KV.get(`actions:${pid}`, { type: "json" });
      if (!stored) return jsonResponse({ status: "empty", envelope: null, envelopes: [] });
      await env.RELAY_KV.delete(`actions:${pid}`);
      const envelopes = Array.isArray(stored) ? stored : [stored];
      return jsonResponse({
        status: "ok",
        envelope: envelopes[envelopes.length - 1] || null,
        envelopes,
      });
    }

    return jsonResponse({ status: "not_found" }, 404);
  },
};

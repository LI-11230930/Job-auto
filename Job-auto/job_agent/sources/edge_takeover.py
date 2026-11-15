"""CDP takeover collector for user-opened normal Microsoft Edge (--remote-debugging-port).

How it stays compliant & avoids Boss直聘 auto-back loops:
- User launches normal Edge (via scripts/open_edge.bat, NO --enable-automation flag,
  so navigator.webdriver === false), manually logs in, and sets search filters.
- When the user says "take over", this module connects over localhost CDP (127.0.0.1:9222),
  scrolls open job portal tabs down smoothly until no new cards load (or Next pages),
  stops immediately on any verification/login wall (zero CAPTCHA bypass), extracts cards
  and HTML snapshots, and disconnects without closing the user's browser window.
"""

from __future__ import annotations

import contextlib
import random
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .assisted_browser import normalize_dom_rows
from .html_import import extract_jobs_from_snapshot

_GATE_MARKERS = ("滑动验证", "安全验证", "请完成验证", "行为验证", "扫码登录", "请先登录")

_SCROLL_PROBE_JS = """
() => {
  const headText = (document.body ? document.body.innerText : '').slice(0, 3500);
  const url = window.location.href || '';
  const step = Math.max(500, Math.round(window.innerHeight * 0.85));
  window.scrollBy({ top: step, behavior: 'smooth' });
  const containers = document.querySelectorAll(
    '.job-list-box, .job-list-wrapper, .position-list, .el-scrollbar__wrap, main'
  );
  containers.forEach((c) => {
    if (c && c.scrollHeight > c.clientHeight + 40) {
      c.scrollTop = Math.min(c.scrollHeight, c.scrollTop + step);
    }
  });
  const maxContainerHeight = Array.from(containers).reduce(
    (mx, el) => Math.max(mx, el ? el.scrollHeight : 0), 0
  );
  const scrollHeight = Math.max(
    document.documentElement ? document.documentElement.scrollHeight : 0,
    document.body ? document.body.scrollHeight : 0,
    maxContainerHeight
  );
  const cardCount = document.querySelectorAll(
    '.job-card-wrapper, li.job-card-box, .position-list__item, .joblist-box__item, .joblist-item, .j_joblist .e, [data-intern-id]'
  ).length;
  return { url, headText, scrollHeight, cardCount };
}
"""

_EXTRACT_DOM_JS = """
(site) => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const url = window.location.href;
  const rows = [];
  if (site === 'zhipin') {
    document.querySelectorAll('.job-card-wrapper, li.job-card-box').forEach((el) => {
      const a = el.querySelector('a.job-name, a.job-title, a[href*="job_detail"]');
      const title = clean(a?.textContent || el.querySelector('.job-name')?.textContent);
      const company = clean(el.querySelector('.company-name a, .company-name, .boss-name')?.textContent);
      const city = clean(el.querySelector('.job-area, .company-location')?.textContent);
      const salary = clean(el.querySelector('.salary, .job-salary')?.textContent);
      const tags = Array.from(el.querySelectorAll('.tag-list li, .job-tag, ul li'))
        .map((t) => clean(t.textContent)).filter(Boolean).slice(0, 8);
      if (title && company) rows.push({ title, company, city, salary, tags, url: a?.href || url });
    });
  } else if (site === 'zhaopin') {
    document.querySelectorAll('.position-list__item, .position-card').forEach((el) => {
      const card = el.classList.contains('position-card') ? el : (el.querySelector('.position-card') || el);
      const title = clean(card.querySelector('.position-card__job-name')?.textContent);
      const company = clean(card.querySelector('.position-card__company__name')?.textContent);
      const city = clean(card.querySelector('.position-card__city-name')?.textContent).replace(/[「」\\[\\]()]/g, '');
      const salary = clean(card.querySelector('.position-card__salary')?.textContent);
      const tags = Array.from(card.querySelectorAll('.position-card__tags__item'))
        .map((t) => clean(t.textContent)).filter(Boolean).slice(0, 8);
      let jobUrl = '';
      const rawOpt = card.getAttribute('data-sensors-exposure-option') || '';
      const m = rawOpt.match(/"jdno"\\s*:\\s*"([A-Za-z0-9_]+)"/);
      if (m) jobUrl = `https://jobs.zhaopin.com/${m[1]}.htm`;
      if (title && company) rows.push({ title, company, city, salary, tags, url: jobUrl || url });
    });
    if (rows.length === 0) {
      document.querySelectorAll('.joblist-box__item, .positionlist__item').forEach((el) => {
        const title = clean(el.querySelector('.jobinfo__name, a[class*="job"]')?.textContent);
        const company = clean(el.querySelector('.companyinfo__name, a[class*="company"]')?.textContent);
        const infoItems = Array.from(el.querySelectorAll('.jobinfo__other-info-item')).map((x) => clean(x.textContent));
        const a = el.querySelector('a.jobinfo__name, a[href*="zhaopin.com"]');
        const salary = clean(el.querySelector('.jobinfo__salary')?.textContent);
        if (title && company) rows.push({ title, company, city: infoItems[0] || '', salary, tags: infoItems.slice(1, 6), url: a?.href || url });
      });
    }
  } else if (site === '51job') {
    document.querySelectorAll('.joblist-item, .j_joblist .e').forEach((el) => {
      const title = clean(el.querySelector('.jname, .job-name')?.textContent);
      const company = clean(el.querySelector('.cname, .comp-name')?.textContent);
      const city = clean(el.querySelector('.area, .d.at')?.textContent);
      const salary = clean(el.querySelector('.sal, .salary')?.textContent);
      const a = el.querySelector('a[href*="51job.com"]');
      if (title && company) rows.push({ title, company, city, salary, tags: [], url: a?.href || url });
    });
  } else if (site === 'iguopin') {
    document.querySelectorAll('a[href*="/job/detail/"]').forEach((a) => {
      const card = a.closest('div[class*="item"], li, .el-card') || a.parentElement?.parentElement;
      if (!card) return;
      const title = clean(card.querySelector('[class*="job-name"], [class*="title"], h3, h4')?.textContent || a.textContent);
      const company = clean(card.querySelector('[class*="company"], [class*="corp"], [class*="org"]')?.textContent);
      const city = clean(card.querySelector('[class*="city"], [class*="area"], [class*="location"]')?.textContent);
      if (title && company) rows.push({ title, company, city, salary: '', tags: [], url: a.href || url });
    });
  } else if (site === 'shixiseng') {
    document.querySelectorAll('.intern-wrap, [data-intern-id]').forEach((el) => {
      const a = el.querySelector('a.title, a[href*="/intern/"]');
      const title = clean(a?.textContent);
      const company = clean(el.querySelector('a[href*="/com/"], .company-name')?.textContent);
      const city = clean(el.querySelector('.city-ellipsis, .city')?.textContent);
      if (title && company) rows.push({ title, company, city, salary: '', tags: ['实习'], url: a?.href || url });
    });
  }
  return rows;
}
"""

_NEXT_BTN_JS = """
(site) => {
  const bySite = {
    zhipin: ['.options-pages a.next:not(.disabled)', 'a i.ui-icon-arrow-right'],
    '51job': ['.el-pagination button.btn-next:not([disabled])', 'li.next:not(.disabled) a'],
    iguopin: ['.el-pagination button.btn-next:not([disabled])'],
    zhaopin: [
      '.pagination__arrow-next:not(.pagination__arrow-next--disabled)',
      '.soupager a.btn:last-child',
      'button.btn-next:not([disabled])',
      '.el-pagination button.btn-next:not([disabled])',
    ],
    shixiseng: [
      'button.btn-next:not([disabled])',
      '.el-pagination button.btn-next:not([disabled])',
    ],
  };
  for (const sel of (bySite[site] || ['.el-pagination button.btn-next:not([disabled])'])) {
    const el = document.querySelector(sel);
    if (el) {
      const target = (el.tagName === 'I' && el.parentElement) ? el.parentElement : el;
      target.scrollIntoView({ block: 'center' });
      target.click();
      return true;
    }
  }
  return false;
}
"""


def detect_tab_site(url: str) -> str:
    low = (url or "").lower()
    if "zhipin.com" in low:
        return "zhipin"
    if "zhaopin.com" in low:
        return "zhaopin"
    if "51job.com" in low:
        return "51job"
    if "iguopin.com" in low:
        return "iguopin"
    if "shixiseng.com" in low:
        return "shixiseng"
    return ""


def is_gated_page(url: str, body_head: str) -> bool:
    low = (url or "").lower()
    if any(k in low for k in ("login", "passport", "verify", "captcha")):
        return True
    return any(m in (body_head or "")[:3500] for m in _GATE_MARKERS)


def _safe_evaluate(page: Any, script: str, arg: Any = None, retries: int = 2) -> Any:
    """Run page.evaluate safely if an SPA navigation briefly destroys the context."""
    from playwright.sync_api import Error as PlaywrightError

    for attempt in range(retries + 1):
        try:
            return page.evaluate(script, arg) if arg is not None else page.evaluate(script)
        except PlaywrightError as exc:
            if "Execution context was destroyed" in str(exc) and attempt < retries:
                with contextlib.suppress(PlaywrightError):
                    page.wait_for_load_state("domcontentloaded", timeout=6000)
                time.sleep(0.8)
                continue
            raise
    return None


DEFAULT_SWEEP_ZHAOPIN_FILTERS: tuple[tuple[str, int], ...] = (
    ("", 4),
    ("会计学", 3),
    ("财务管理", 3),
    ("会计", 3),
    ("金融学", 3),
    ("人力资源管理", 3),
    ("工商管理", 3),
    ("电子商务", 2),
    ("计算机科学与技术", 2),
)

DEFAULT_SWEEP_SHIXISENG_QUERIES: tuple[tuple[str, str, int], ...] = (
    ("太原", "", 4),
    ("济南", "", 3),
    ("青岛", "", 3),
    ("西安", "", 4),
    ("全国", "", 4),
    ("全国", "会计", 3),
    ("全国", "审计", 3),
    ("全国", "财务", 3),
    ("全国", "财务分析", 2),
    ("全国", "实施", 2),
    ("全国", "管培", 3),
    ("全国", "人力资源", 3),
    ("全国", "运营", 3),
    ("全国", "数据分析", 3),
    ("全国", "金融", 3),
    ("全国", "AI", 3),
)


def _collect_paginated_page(
    page: Any,
    *,
    site: str,
    snap_prefix: str,
    save_snapshot_dir: Path | None,
    max_scrolls: int,
    max_pages: int,
    page_delay_seconds: float,
    exclude_social: bool,
    dedup: dict[str, dict[str, Any]],
    on_page_jobs: Callable[[list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    """Scroll, capture snapshot/DOM, and follow Next pagination on one Playwright page."""
    from playwright.sync_api import Error as PlaywrightError

    tab_extracted = 0
    pages_done = 0
    gated = False
    stop_reason = "completed"

    try:
        for page_num in range(1, max(1, max_pages) + 1):
            last_h = 0
            last_c = 0
            stagnant = 0
            for _scroll in range(max_scrolls):
                probe = _safe_evaluate(page, _SCROLL_PROBE_JS)
                if not probe or is_gated_page(probe.get("url", ""), probe.get("headText", "")):
                    gated = True
                    stop_reason = "gated_verification_or_login"
                    break
                cur_h = int(probe.get("scrollHeight") or 0)
                cur_c = int(probe.get("cardCount") or 0)
                if cur_h <= last_h + 20 and cur_c <= last_c:
                    stagnant += 1
                else:
                    stagnant = 0
                    last_h = cur_h
                    last_c = cur_c
                if stagnant >= 3:
                    stop_reason = "reached_bottom"
                    break
                time.sleep(random.uniform(1.1, 1.8))

            if gated:
                break

            html_text = page.content()
            if save_snapshot_dir:
                snap = save_snapshot_dir / site / f"{snap_prefix}_p{page_num}.html"
                snap.parent.mkdir(parents=True, exist_ok=True)
                snap.write_text(html_text, encoding="utf-8")

            dom_rows = _safe_evaluate(page, _EXTRACT_DOM_JS, site) or []
            page_jobs = normalize_dom_rows(
                dom_rows, site=site, exclude_social=exclude_social
            )
            seen_hashes = {j["dedup_hash"] for j in page_jobs}
            for job in extract_jobs_from_snapshot(
                html_text, site=site, filename_hint=page.url, exclude_social=exclude_social
            ):
                if job["dedup_hash"] not in seen_hashes:
                    page_jobs.append(job)
                    seen_hashes.add(job["dedup_hash"])

            tab_extracted += len(page_jobs)
            for job in page_jobs:
                dedup.setdefault(job["dedup_hash"], job)
            if on_page_jobs and page_jobs:
                on_page_jobs(page_jobs)
            pages_done += 1

            if page_num < max_pages:
                moved = bool(_safe_evaluate(page, _NEXT_BTN_JS, site))
                if not moved:
                    break
                with contextlib.suppress(PlaywrightError):
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                time.sleep(page_delay_seconds + random.uniform(0.3, 1.1))
    except PlaywrightError as exc:
        stop_reason = f"tab_error:{type(exc).__name__}"

    return {
        "site": site,
        "url": page.url,
        "pages": pages_done,
        "extracted": tab_extracted,
        "gated": gated,
        "stop_reason": stop_reason,
    }


def collect_from_open_edge_cdp(
    *,
    cdp_url: str = "http://127.0.0.1:9222",
    site_filter: str = "auto",
    save_snapshot_dir: Path | None = None,
    max_scrolls: int = 30,
    max_pages: int = 1,
    page_delay_seconds: float = 4.5,
    exclude_social: bool = True,
) -> dict[str, Any]:
    """Attach to user's already-running normal Edge via CDP, scroll to bottom, and collect jobs."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    if save_snapshot_dir:
        save_snapshot_dir.mkdir(parents=True, exist_ok=True)

    dedup: dict[str, dict[str, Any]] = {}
    tab_reports: list[dict[str, Any]] = []
    session_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        try:
            target_pages: list[tuple[str, Any]] = []
            for ctx in browser.contexts:
                for page in ctx.pages:
                    site = detect_tab_site(page.url)
                    if not site:
                        continue
                    if site_filter != "auto" and site != site_filter:
                        continue
                    target_pages.append((site, page))

            for idx, (site, page) in enumerate(target_pages, start=1):
                with contextlib.suppress(PlaywrightError):
                    page.bring_to_front()
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                rep = _collect_paginated_page(
                    page,
                    site=site,
                    snap_prefix=f"cdp_{session_tag}_t{idx}",
                    save_snapshot_dir=save_snapshot_dir,
                    max_scrolls=max_scrolls,
                    max_pages=max_pages,
                    page_delay_seconds=page_delay_seconds,
                    exclude_social=exclude_social,
                    dedup=dedup,
                )
                tab_reports.append(rep)
        finally:
            # Disconnects CDP client only; leaves user's normal Edge open
            browser.close()

    return {"tabs": tab_reports, "jobs": list(dedup.values())}


def collect_portal_sweep_cdp(
    *,
    cdp_url: str = "http://127.0.0.1:9222",
    site_filter: str = "all",
    save_snapshot_dir: Path | None = None,
    max_scrolls: int = 8,
    page_delay_seconds: float = 2.4,
    exclude_social: bool = False,
    on_batch: Callable[[list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    """Recurring multi-query sweep across open Zhaopin Campus & Shixiseng tabs in Edge."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    dedup: dict[str, dict[str, Any]] = {}
    query_reports: list[dict[str, Any]] = []
    session_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        try:
            pages = [pg for ctx in browser.contexts for pg in ctx.pages]
            zhaopin_pg = next((pg for pg in pages if "zhaopin.com" in pg.url), None)
            sxs_pg = next((pg for pg in pages if "shixiseng.com" in pg.url), None)

            if site_filter in ("all", "zhaopin") and zhaopin_pg is not None:
                for idx, (pill_text, max_p) in enumerate(DEFAULT_SWEEP_ZHAOPIN_FILTERS, start=1):
                    try:
                        zhaopin_pg.goto(
                            "https://xiaoyuan.zhaopin.com/search/index?refcode=4485",
                            wait_until="domcontentloaded",
                            timeout=18000,
                        )
                        time.sleep(2.2)
                        if pill_text:
                            loc = zhaopin_pg.get_by_text(pill_text, exact=True).first
                            if loc.count() > 0:
                                loc.click()
                                time.sleep(2.2)
                        rep = _collect_paginated_page(
                            zhaopin_pg,
                            site="zhaopin",
                            snap_prefix=f"sweep_{session_tag}_zp_{idx}",
                            save_snapshot_dir=save_snapshot_dir,
                            max_scrolls=max_scrolls,
                            max_pages=max_p,
                            page_delay_seconds=page_delay_seconds,
                            exclude_social=exclude_social,
                            dedup=dedup,
                            on_page_jobs=on_batch,
                        )
                        rep["query"] = pill_text or "不限"
                        query_reports.append(rep)
                        if rep["gated"]:
                            break
                    except PlaywrightError as exc:
                        query_reports.append(
                            {
                                "site": "zhaopin",
                                "query": pill_text or "不限",
                                "pages": 0,
                                "extracted": 0,
                                "gated": False,
                                "stop_reason": f"nav_error:{type(exc).__name__}",
                            }
                        )

            if site_filter in ("all", "shixiseng") and sxs_pg is not None:
                for idx, (city, kw, max_p) in enumerate(DEFAULT_SWEEP_SHIXISENG_QUERIES, start=1):
                    try:
                        url = (
                            f"https://www.shixiseng.com/interns?keyword={quote(kw)}"
                            f"&city={quote(city)}"
                        )
                        sxs_pg.goto(url, wait_until="domcontentloaded", timeout=18000)
                        time.sleep(2.2)
                        rep = _collect_paginated_page(
                            sxs_pg,
                            site="shixiseng",
                            snap_prefix=f"sweep_{session_tag}_sxs_{idx}",
                            save_snapshot_dir=save_snapshot_dir,
                            max_scrolls=max_scrolls,
                            max_pages=max_p,
                            page_delay_seconds=page_delay_seconds,
                            exclude_social=exclude_social,
                            dedup=dedup,
                            on_page_jobs=on_batch,
                        )
                        rep["query"] = f"{city}:{kw or '全岗'}"
                        query_reports.append(rep)
                        if rep["gated"]:
                            break
                    except PlaywrightError as exc:
                        query_reports.append(
                            {
                                "site": "shixiseng",
                                "query": f"{city}:{kw or '全岗'}",
                                "pages": 0,
                                "extracted": 0,
                                "gated": False,
                                "stop_reason": f"nav_error:{type(exc).__name__}",
                            }
                        )
        finally:
            browser.close()

    return {"queries": query_reports, "jobs": list(dedup.values())}

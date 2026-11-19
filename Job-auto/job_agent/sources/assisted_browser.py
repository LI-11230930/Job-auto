"""User-assisted headed browser collector for login/anti-bot-gated job portals.

Compliance & Ethics Notice:
- Never uses stealth plugins or automated CAPTCHA/slider solvers.
- Launches a normal visible Edge/Chrome browser profile where the user logs in,
  solves any verification themselves, and sets initial search filters.
- Supports both interactive single-page capture and polite paced auto-pagination
  (auto-exports raw HTML snapshots to data/inbox/<site>/ and pauses immediately
  if any login wall or verification challenge appears).
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import compute_dedup_hash, infer_channel, split_cities
from .html_import import _infer_job_type, extract_jobs_from_snapshot

SITE_URLS: dict[str, str] = {
    "zhipin": "https://www.zhipin.com/",
    "51job": "https://www.51job.com/",
    "iguopin": "https://www.iguopin.com/job",
    "zhaopin": "https://www.zhaopin.com/",
}

_GATE_MARKERS = ("滑动验证", "安全验证", "请完成验证", "行为验证", "扫码登录", "请先登录")

_NEXT_PAGE_SELECTORS: dict[str, tuple[str, ...]] = {
    "zhipin": (".options-pages a.next:not(.disabled)", "a:has(i.ui-icon-arrow-right)"),
    "51job": (".el-pagination button.btn-next:not([disabled])", "li.next:not(.disabled) a"),
    "iguopin": (
        ".ant-pagination-next:not(.ant-pagination-disabled):not([aria-disabled='true']) button",
        "li[title='下一页'][aria-disabled='false'] button",
        ".el-pagination button.btn-next:not([disabled])",
        "button:has-text('下一页')",
    ),
    "zhaopin": (".soupager a.btn:has-text('下一页')", "button:has-text('下一页')"),
}

_DOM_EXTRACT_JS = """
(site) => {
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const rows = [];
  if (site === 'zhipin') {
    document.querySelectorAll('.job-card-wrapper, li.job-card-box').forEach((el) => {
      const a = el.querySelector('a.job-name, a.job-title, a[href*="job_detail"]');
      const title = clean(a?.textContent || el.querySelector('.job-name')?.textContent);
      const company = clean(el.querySelector('.company-name a, .company-name, .boss-name')?.textContent);
      const city = clean(el.querySelector('.job-area, .company-location')?.textContent);
      const salary = clean(el.querySelector('.salary, .job-salary')?.textContent);
      const tags = Array.from(el.querySelectorAll('.tag-list li, .job-tag')).map((t) => clean(t.textContent)).filter(Boolean);
      const url = a?.href || '';
      if (title && company) rows.push({ title, company, city, salary, tags, url });
    });
  } else if (site === '51job') {
    document.querySelectorAll('.joblist-item, .j_joblist .e').forEach((el) => {
      const title = clean(el.querySelector('.jname, .job-name')?.textContent);
      const company = clean(el.querySelector('.cname, .comp-name')?.textContent);
      const city = clean(el.querySelector('.area, .d.at')?.textContent);
      const salary = clean(el.querySelector('.sal, .salary')?.textContent);
      const a = el.querySelector('a[href*="51job.com"]');
      const url = a?.href || '';
      if (title && company) rows.push({ title, company, city, salary, tags: [], url });
    });
  } else if (site === 'iguopin') {
    document.querySelectorAll('.job-card').forEach((el) => {
      const title = clean((el.querySelector('.job-name') || el.querySelector('[class*="job-name"]') || el.querySelector('[class*="title"], h3, h4'))?.textContent);
      const company = clean(el.querySelector('a.company-name, .company-name, .department-name, [class*="company"], [class*="corp"], [class*="org"]')?.textContent);
      const city = clean(el.querySelector('.job-district, [class*="district"], [class*="city"], [class*="area"], [class*="location"]')?.textContent).replace(/[「」\\[\\]()]/g, '');
      const salary = clean(el.querySelector('.job-salary, [class*="salary"]')?.textContent);
      const tags = Array.from(el.querySelectorAll('.job-info .tag-item, .job-tag .ant-tag, .company-info .company-info-item'))
        .map((t) => clean(t.textContent)).filter(Boolean);
      const trackerId = clean(el.getAttribute('data-tracker'));
      const a = el.querySelector('a[href*="/job/detail"]');
      const jobUrl = a?.href || (trackerId ? `https://www.iguopin.com/job/detail?id=${trackerId}` : '');
      if (title && company) rows.push({ title, company, city, salary, tags, url: jobUrl });
    });
    if (rows.length === 0) {
      document.querySelectorAll('a[href*="/job/detail/"]').forEach((a) => {
        const card = a.closest('div[class*="item"], li, .el-card') || a.parentElement?.parentElement;
        if (!card) return;
        const title = clean(card.querySelector('[class*="job-name"], [class*="title"], h3, h4')?.textContent || a.textContent);
        const company = clean(card.querySelector('[class*="company"], [class*="corp"], [class*="org"]')?.textContent);
        const city = clean(card.querySelector('[class*="city"], [class*="area"], [class*="location"]')?.textContent).replace(/[「」\\[\\]()]/g, '');
        if (title && company) rows.push({ title, company, city, salary: '', tags: [], url: a.href });
      });
    }
  } else if (site === 'zhaopin') {
    document.querySelectorAll('.joblist-box__item, [class*="positionlist-item"]').forEach((el) => {
      const a = el.querySelector('a[href*="jobdetail"]');
      const title = clean(el.querySelector('[class*="jobinfo__name"], .job-name')?.textContent || a?.textContent);
      const company = clean(el.querySelector('[class*="companyinfo__name"], .company-name')?.textContent);
      const city = clean(el.querySelector('[class*="other-info__item"], .job-area')?.textContent);
      const salary = clean(el.querySelector('[class*="salary"]')?.textContent);
      if (title && company) rows.push({ title, company, city, salary, tags: [], url: a?.href || '' });
    });
  }
  return rows;
}
"""


def normalize_dom_rows(
    rows: list[dict[str, Any]],
    *,
    site: str,
    exclude_social: bool = True,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for row in rows:
        title = str(row.get("title") or "").strip()
        company = str(row.get("company") or "").strip()
        if not title or not company:
            continue
        tags = row.get("tags") or []
        hint = " ".join(str(t) for t in tags)
        job_type = _infer_job_type(title, hint)
        if exclude_social and job_type == "社招":
            continue
        city_raw = str(row.get("city") or "").strip()
        url = str(row.get("url") or "").strip()
        salary = str(row.get("salary") or "").strip()
        apply_channel, apply_target, priority_rank = infer_channel(url, "", site)
        jd_lines = [f"【来源平台】{site}（人工辅助浏览器采集）"]
        if salary:
            jd_lines.append(f"【薪资范围】{salary}")
        if city_raw:
            jd_lines.append(f"【工作地点】{city_raw}")
        if tags:
            jd_lines.append(f"【要求标签】{'、'.join(str(t) for t in tags[:10])}")
        jobs.append(
            {
                "source": site,
                "source_job_id": url or f"{company}:{title}",
                "company": company,
                "title": title,
                "cities": split_cities(city_raw),
                "job_type": job_type,
                "jd_text": "\n".join(jd_lines),
                "url": url,
                "apply_channel": apply_channel,
                "apply_target": apply_target,
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": compute_dedup_hash(
                    company=company,
                    title=title,
                    job_type=job_type,
                    official_req_id="",
                ),
                "priority_rank": priority_rank,
            }
        )
    return jobs


def _is_page_gated(html_content: str, url: str) -> bool:
    if any(k in url.lower() for k in ("login", "passport", "verify", "captcha")):
        return True
    visible_head = html_content[:8000]
    return any(marker in visible_head for marker in _GATE_MARKERS)


def _click_next_page(page: Any, site: str) -> bool:
    for selector in _NEXT_PAGE_SELECTORS.get(site, ()):
        locator = page.locator(selector).first
        if locator.count() > 0 and locator.is_visible():
            locator.scroll_into_view_if_needed()
            locator.click()
            page.wait_for_timeout(1500)
            return True
    return False


def collect_via_assisted_browser(
    *,
    site: str,
    user_data_dir: Path,
    exclude_social: bool = True,
    save_snapshot_dir: Path | None = None,
    auto_pages: int = 3,
    page_delay_seconds: float = 4.5,
) -> list[dict[str, Any]]:
    """Open a persistent headed browser for user login/filtering, then auto-paginate & export."""
    if site not in SITE_URLS:
        raise ValueError(f"Unsupported site '{site}'. Choose from: {', '.join(SITE_URLS)}")

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    user_data_dir.mkdir(parents=True, exist_ok=True)
    if save_snapshot_dir:
        save_snapshot_dir.mkdir(parents=True, exist_ok=True)

    collected: dict[str, dict[str, Any]] = {}
    session_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    def capture_current_page(page_obj: Any, idx: int) -> tuple[int, int, bool]:
        html_content = page_obj.content()
        if _is_page_gated(html_content, page_obj.url):
            return 0, 0, True
        if save_snapshot_dir:
            snap = save_snapshot_dir / f"{site}_{session_tag}_p{idx}.html"
            snap.write_text(html_content, encoding="utf-8")
        dom_rows = page_obj.evaluate(_DOM_EXTRACT_JS, site)
        jobs = normalize_dom_rows(dom_rows, site=site, exclude_social=exclude_social)
        if not jobs:
            jobs = extract_jobs_from_snapshot(
                html_content, site=site, exclude_social=exclude_social
            )
        new_cnt = 0
        for job in jobs:
            if job["dedup_hash"] not in collected:
                new_cnt += 1
            collected[job["dedup_hash"]] = job
        return len(jobs), new_cnt, False

    if site == "zhipin":
        print(
            "[提示] Boss直聘对自动化浏览器标志较为敏感，若窗口出现自动回退循环，请改用：\n"
            "  1) 双击运行 scripts/listen_inbox.bat（启动本地接收端口 127.0.0.1:8765）；\n"
            "  2) 在日常普通 Edge 中加载 extensions/job_auto_collector 扩展，打开 zhipin.com 后点扩展一键采集。"
        )
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                channel="msedge",
                headless=False,
            )
        except PlaywrightError:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
            )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(SITE_URLS[site], wait_until="domcontentloaded")
        print(
            f"\n[人工辅助浏览器采集 - {site}]\n"
            "1. 请在打开的 Edge 窗口中完成登录、验证与城市/关键词筛选（登录态会保留在本地 profile）。\n"
            "2. 停留到目标搜索结果页后，回终端选择：\n"
            f"   - 直接按回车：低频自动翻页采集并导出 HTML 快照（默认最多 {auto_pages} 页，每页间隔 ~{page_delay_seconds}s）\n"
            "   - 输入数字（如 5）：低频自动翻页 5 页\n"
            "   - 输入 m：手动逐页按回车抓取\n"
            "   - 输入 q：退出\n"
        )
        page_idx = 0
        while True:
            cmd = input(f"[{site}] 请选择 ([Enter]=自动{auto_pages}页 / 数字 / m=手动 / q=退出): ").strip().lower()
            if cmd == "q":
                break
            if cmd == "m":
                page_idx += 1
                total_p, new_p, gated = capture_current_page(page, page_idx)
                if gated:
                    print("  [暂停] 检测到登录或验证门禁，请在浏览器中处理完成后再按回车重试。")
                    continue
                print(
                    f"  -> 第 {page_idx} 页捕获 {total_p} 条，新增去重 {new_p} 条"
                    f"（累计 {len(collected)} 条，已自动导出快照）"
                )
                continue

            target_pages = int(cmd) if cmd.isdigit() and int(cmd) > 0 else max(1, auto_pages)
            for step in range(target_pages):
                page_idx += 1
                page.mouse.wheel(0, 1400)
                page.wait_for_timeout(800)
                total_p, new_p, gated = capture_current_page(page, page_idx)
                if gated:
                    print(
                        "  [暂停保护] 检测到安全验证或登录提示，已立即停止翻页；"
                        "请在浏览器完成验证后回到终端继续。"
                    )
                    break
                print(
                    f"  -> 第 {page_idx} 页捕获 {total_p} 条，新增去重 {new_p} 条"
                    f"（累计 {len(collected)} 条，已导出快照）"
                )
                if step == target_pages - 1:
                    break
                sleep_sec = page_delay_seconds + random.uniform(0.5, 2.2)
                print(f"  ...礼貌等待 {sleep_sec:.1f}s 后尝试下一页...")
                time.sleep(sleep_sec)
                if not _click_next_page(page, site):
                    print("  -> 未找到可用的下一页按钮，本轮自动翻页结束。")
                    break

        context.close()

    return list(collected.values())

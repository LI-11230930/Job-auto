"""Public SSR adapter for Shixiseng (实习僧, shixiseng.com)."""

from __future__ import annotations

import html as _html
import re
import time
from collections.abc import Iterator, Sequence
from typing import Any
from urllib.parse import quote

import httpx

from .base import compute_dedup_hash, infer_channel, split_cities

DEFAULT_SHIXISENG_KEYWORDS: tuple[str, ...] = ("财务", "会计", "审计", "税务", "ERP")
DEFAULT_SHIXISENG_CITIES: tuple[str, ...] = ("全国", "太原", "济南", "青岛", "西安")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_PUA_RE = re.compile(r"[\ue000-\uf8ff]")
_CARD_SPLIT_RE = re.compile(r'<div[^>]*data-intern-id="([^"]+)"[^>]*>')


def _clean_shixiseng_text(raw: str) -> str:
    text = _html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = _PUA_RE.sub("", text)
    return " ".join(text.split())


def parse_shixiseng_html(html_text: str) -> list[dict[str, Any]]:
    """Parse Shixiseng Nuxt SSR search result cards cleanly."""
    parts = _CARD_SPLIT_RE.split(html_text)
    if len(parts) < 3:
        return []

    jobs: list[dict[str, Any]] = []
    # parts alternates: [prefix, intern_id_1, block_1, intern_id_2, block_2, ...]
    for idx in range(1, len(parts) - 1, 2):
        intern_id = parts[idx].strip()
        block = parts[idx + 1][:4000]
        url_m = re.search(r'href="(https://www\.shixiseng\.com/intern/[^"?]+)', block)
        if not url_m:
            continue
        detail_url = url_m.group(1).strip()

        title_m = re.search(r'class="title ellipsis font"[^>]*>(.*?)</a>', block, re.DOTALL)
        title = _clean_shixiseng_text(title_m.group(1)) if title_m else ""

        comp_m = re.search(
            r'<a[^>]*title="([^"]+)"[^>]*class="title ellipsis"', block
        ) or re.search(r'<a[^>]*class="title ellipsis"[^>]*>([^<]+)</a>', block)
        company = _clean_shixiseng_text(comp_m.group(1)) if comp_m else ""
        if not company or not title:
            continue

        city_m = re.search(r'class="city ellipsis"[^>]*>(.*?)</span>', block, re.DOTALL)
        raw_city = _clean_shixiseng_text(city_m.group(1)) if city_m else ""
        cities = split_cities(raw_city)

        apply_channel, apply_target, priority_rank = infer_channel(detail_url, "", "shixiseng")
        jobs.append(
            {
                "source": "shixiseng",
                "source_job_id": intern_id,
                "company": company,
                "title": title,
                "cities": cities,
                "job_type": "实习",
                "jd_text": f"【来源平台】实习僧\n【城市】{raw_city or '未标明'}",
                "url": detail_url,
                "apply_channel": apply_channel,
                "apply_target": apply_target,
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": compute_dedup_hash(
                    company=company,
                    title=title,
                    job_type="实习",
                    official_req_id=intern_id,
                ),
                "priority_rank": priority_rank,
            }
        )
    return jobs


class ShixisengPublicAdapter:
    """Polite SSR adapter for Shixiseng intern listings."""

    source_name = "shixiseng"

    def __init__(
        self,
        *,
        cities: Sequence[str] = DEFAULT_SHIXISENG_CITIES,
        keywords: Sequence[str] = DEFAULT_SHIXISENG_KEYWORDS,
        max_pages: int = 1,
        request_interval: float = 0.45,
    ) -> None:
        self.cities = list(cities)
        self.keywords = list(keywords)
        self.max_pages = max(1, max_pages)
        self.request_interval = request_interval
        self.errors: list[str] = []

    def fetch_jobs(self) -> Iterator[dict[str, Any]]:
        seen_hashes: set[str] = set()
        with httpx.Client(
            headers=_HEADERS,
            timeout=12.0,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            for city in self.cities:
                for kw in self.keywords:
                    for page in range(1, self.max_pages + 1):
                        if self.request_interval > 0:
                            time.sleep(self.request_interval)
                        url = (
                            f"https://www.shixiseng.com/interns"
                            f"?keyword={quote(kw)}&city={quote(city)}&page={page}"
                        )
                        try:
                            resp = client.get(url)
                            resp.raise_for_status()
                        except httpx.HTTPError as exc:
                            self.errors.append(f"shixiseng {city}/{kw}/p{page}: {exc}")
                            break
                        jobs = parse_shixiseng_html(resp.text)
                        if not jobs:
                            break
                        for job in jobs:
                            dh = job["dedup_hash"]
                            if dh not in seen_hashes:
                                seen_hashes.add(dh)
                                yield job

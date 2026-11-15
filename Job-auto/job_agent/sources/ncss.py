"""Public adapter for 国家大学生就业服务平台 (NCSS / 教育部 24365, ncss.cn)."""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from .base import (
    DEFAULT_ALLOWED_SCHOOLS,
    OPEN_PUBLIC_NCSS_SOURCES,
    compute_dedup_hash,
    infer_channel,
    split_cities,
)

NCSS_LIST_URL = "https://www.ncss.cn/student/jobs/jobslist/ajax/"

DEFAULT_NCSS_AREA_CODES: tuple[tuple[str, str], ...] = (
    ("140100", "太原"),
    ("140200", "大同"),
    ("140300", "阳泉"),
    ("140400", "长治"),
    ("140500", "晋城"),
    ("140600", "朔州"),
    ("140700", "晋中"),
    ("140800", "运城"),
    ("140900", "忻州"),
    ("141000", "临汾"),
    ("141100", "吕梁"),
    ("370100", "济南"),
    ("370200", "青岛"),
    ("610100", "西安"),
)

DEFAULT_NCSS_KEYWORDS: tuple[str, ...] = ("财务", "会计", "审计", "管培", "ERP")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.ncss.cn/student/jobs/index.html",
}


def _infer_ncss_job_type(title: str, recruit_type: str) -> str:
    if "实习" in title:
        return "实习"
    # NCSS recruitType: "0"=全职/校招, "1"=实习
    if str(recruit_type).strip() == "1":
        return "实习"
    return "校招"


def _format_ncss_date(ts_ms: Any) -> str:
    if not ts_ms:
        return ""
    try:
        sec = float(ts_ms) / 1000.0
        return datetime.fromtimestamp(sec, tz=UTC).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _is_ncss_item_restricted(
    item: dict[str, Any],
    *,
    allowed_schools: Sequence[str] = DEFAULT_ALLOWED_SCHOOLS,
) -> bool:
    src_name = str(item.get("sourcesNameCh") or "").strip()
    src_type = str(item.get("sourcesType") or "").strip()
    if not src_name:
        return False
    low = src_name.lower()
    if any(tok in low for tok in OPEN_PUBLIC_NCSS_SOURCES):
        return False
    if any(s and s in src_name for s in allowed_schools):
        return False
    return src_type in {"1", "11", "12"} or True


def parse_ncss_payload(
    payload: dict[str, Any],
    *,
    fallback_city: str = "",
    exclude_restricted_campus: bool = True,
    allowed_schools: Sequence[str] = DEFAULT_ALLOWED_SCHOOLS,
) -> list[dict[str, Any]]:
    """Parse one NCSS ajax JSON payload into normalized Job-auto job dicts."""
    data = payload.get("data") or {}
    items = data.get("list") or []
    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if exclude_restricted_campus and _is_ncss_item_restricted(
            item, allowed_schools=allowed_schools
        ):
            continue
        company = str(item.get("recName") or "").strip()
        title = str(item.get("jobName") or "").strip()
        job_id = str(item.get("jobId") or "").strip()
        if not company or not title or not job_id:
            continue

        job_type = _infer_ncss_job_type(title, str(item.get("recruitType") or ""))
        area_name = str(item.get("areaCodeName") or "").strip()
        cities = split_cities(area_name)
        if fallback_city and fallback_city not in cities:
            # NCSS sometimes returns province name ("山西") when querying city code ("140100")
            cities.insert(0, fallback_city)

        detail_url = f"https://www.ncss.cn/student/jobs/{job_id}/detail.html"
        apply_channel, apply_target, priority_rank = infer_channel(detail_url, "", "ncss")

        low_pay = item.get("lowMonthPay")
        high_pay = item.get("highMonthPay")
        salary_str = ""
        if low_pay or high_pay:
            salary_str = f"{low_pay or ''}-{high_pay or ''}K/月".strip("-")

        jd_lines = []
        if item.get("degreeName"):
            jd_lines.append(f"【学历要求】{item['degreeName']}")
        if item.get("major"):
            jd_lines.append(f"【面向专业】{item['major']}")
        if salary_str:
            jd_lines.append(f"【薪资范围】{salary_str}")
        if item.get("recProperty"):
            jd_lines.append(f"【企业性质】{item['recProperty']} | 规模: {item.get('recScale') or ''}")
        if item.get("headCount"):
            jd_lines.append(f"【招聘人数】{item['headCount']}")
        if item.get("sourcesNameCh"):
            jd_lines.append(f"【来源高校/站点】{item['sourcesNameCh']}")
        pub = _format_ncss_date(item.get("publishDate") or item.get("updateDate"))
        if pub:
            jd_lines.append(f"【发布日期】{pub}")

        results.append(
            {
                "source": "ncss",
                "source_job_id": job_id,
                "company": company,
                "title": title,
                "cities": cities,
                "job_type": job_type,
                "jd_text": "\n".join(jd_lines),
                "url": detail_url,
                "apply_channel": apply_channel,
                "apply_target": apply_target,
                "deadline": "",
                "industry": str(item.get("recProperty") or "").strip(),
                "status": "active",
                "dedup_hash": compute_dedup_hash(
                    company=company,
                    title=title,
                    job_type=job_type,
                    official_req_id=job_id,
                ),
                "priority_rank": priority_rank,
            }
        )
    return results


class NcssPublicAdapter:
    """Polite un-gated adapter for NCSS 24365 public campus job search API."""

    source_name = "ncss"

    def __init__(
        self,
        *,
        area_codes: Sequence[tuple[str, str]] = DEFAULT_NCSS_AREA_CODES,
        keywords: Sequence[str] = DEFAULT_NCSS_KEYWORDS,
        max_pages: int = 1,
        page_size: int = 20,
        request_interval: float = 0.35,
    ) -> None:
        self.area_codes = list(area_codes)
        self.keywords = list(keywords)
        self.max_pages = max(1, max_pages)
        self.page_size = page_size
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
            for code, city_name in self.area_codes:
                for kw in self.keywords:
                    for page in range(1, self.max_pages + 1):
                        if self.request_interval > 0:
                            time.sleep(self.request_interval)
                        try:
                            resp = client.get(
                                NCSS_LIST_URL,
                                params={
                                    "jobName": kw,
                                    "areaCode": code,
                                    "limit": self.page_size,
                                    "offset": page,
                                },
                            )
                            resp.raise_for_status()
                            if not resp.text.strip():
                                break
                            payload = resp.json()
                        except (httpx.HTTPError, ValueError) as exc:
                            self.errors.append(f"ncss {city_name}/{kw}/p{page}: {exc}")
                            break

                        jobs = parse_ncss_payload(payload, fallback_city=city_name)
                        if not jobs:
                            break
                        for job in jobs:
                            dh = job["dedup_hash"]
                            if dh not in seen_hashes:
                                seen_hashes.add(dh)
                                yield job
                        if len(jobs) < self.page_size:
                            break

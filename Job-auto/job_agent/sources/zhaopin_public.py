"""Public SSR adapter for Zhaopin (智联招聘, zhaopin.com)."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator, Sequence
from typing import Any
from urllib.parse import quote

import httpx

from .base import compute_dedup_hash, infer_channel, split_cities

DEFAULT_ZHAOPIN_CITIES: tuple[tuple[str, str], ...] = (
    ("576", "太原"),
    ("578", "大同"),
    ("580", "长治"),
    ("583", "晋中"),
    ("584", "运城"),
    ("702", "济南"),
    ("703", "青岛"),
    ("854", "西安"),
)

DEFAULT_ZHAOPIN_KEYWORDS: tuple[str, ...] = (
    "财务管培生",
    "财务实习",
    "财务专员",
    "会计应届",
    "审计实习",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_INITIAL_STATE_RE = re.compile(r"__INITIAL_STATE__=(\{.*?\});?\s*</script>", re.DOTALL)
_SOCIAL_EXP_MARKERS = ("1-3年", "3-5年", "5-10年", "10年以上")
_CAMPUS_HINT_MARKERS = ("27届", "2027", "应届", "校招", "校园", "管培", "实习")


def _classify_zhaopin_job_type(title: str, working_exp: str, is_campus_obj: bool) -> str:
    if "实习" in title:
        return "实习"
    if is_campus_obj or any(k in title for k in _CAMPUS_HINT_MARKERS):
        return "校招"
    exp = (working_exp or "").strip()
    if exp in _SOCIAL_EXP_MARKERS:
        return "社招"
    if exp in {"经验不限", "无经验", "1年以下", "在校/应届", ""}:
        return "校招"
    return "社招"


def is_login_or_captcha_gate(html_text: str, final_url: str = "") -> bool:
    """Detect whether Zhaopin redirected to login or presented a verification gate."""
    lowered_url = (final_url or "").lower()
    if "passport.zhaopin.com" in lowered_url or "captcha" in lowered_url:
        return True
    if "__INITIAL_STATE__" not in html_text:
        return any(
            marker in html_text
            for marker in ("滑动验证", "安全验证", "请登录", "passport.zhaopin.com")
        )
    return False


def parse_zhaopin_html(
    html_text: str,
    *,
    exclude_social: bool = True,
    final_url: str = "",
) -> tuple[list[dict[str, Any]], bool]:
    """Parse Zhaopin SSR search HTML.

    Returns (jobs, gated) where gated=True indicates a login or verification gate
    was encountered so the caller should stop politely rather than retrying.
    """
    if is_login_or_captcha_gate(html_text, final_url=final_url):
        return [], True

    match = _INITIAL_STATE_RE.search(html_text)
    if not match:
        return [], False

    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError:
        return [], False

    position_list = state.get("positionList") or []
    jobs: list[dict[str, Any]] = []
    for item in position_list:
        if not isinstance(item, dict):
            continue
        company = str(item.get("companyName") or "").strip()
        title = str(item.get("name") or "").strip()
        if not company or not title:
            continue

        working_exp = str(item.get("workingExp") or "").strip()
        is_campus_obj = bool(item.get("campusJobDetail"))
        job_type = _classify_zhaopin_job_type(title, working_exp, is_campus_obj)
        if exclude_social and job_type == "社招":
            continue

        work_city = str(item.get("workCity") or "").strip()
        cities = split_cities(work_city)
        pos_url = str(item.get("positionURL") or "").strip()
        source_job_id = str(item.get("number") or item.get("jobId") or pos_url).strip()
        apply_channel, apply_target, priority_rank = infer_channel(pos_url, "", "zhaopin")

        tags: list[str] = []
        raw_labels = item.get("skillLabel") or []
        if isinstance(raw_labels, list):
            tags = [str(x.get("value") or "").strip() for x in raw_labels if isinstance(x, dict)]
            tags = [t for t in tags if t]

        jd_lines = []
        if working_exp or item.get("education"):
            jd_lines.append(
                f"【基本要求】经验：{working_exp or '不限'} | 学历：{item.get('education') or '不限'}"
            )
        if item.get("salary60"):
            jd_lines.append(f"【薪资范围】{item['salary60']}")
        if item.get("cityDistrict"):
            jd_lines.append(f"【工作区域】{work_city} - {item['cityDistrict']}")
        if item.get("property") or item.get("companySize"):
            jd_lines.append(
                f"【企业信息】{item.get('property') or ''} | {item.get('companySize') or ''}"
            )
        if tags:
            jd_lines.append(f"【职位标签】{'、'.join(tags[:10])}")
        if item.get("jobSummary"):
            jd_lines.append(f"【岗位摘要】\n{item['jobSummary']}")

        jobs.append(
            {
                "source": "zhaopin",
                "source_job_id": source_job_id,
                "company": company,
                "title": title,
                "cities": cities,
                "job_type": job_type,
                "jd_text": "\n".join(jd_lines),
                "url": pos_url,
                "apply_channel": apply_channel,
                "apply_target": apply_target,
                "deadline": "",
                "industry": str(item.get("industryName") or item.get("property") or "").strip(),
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
    return jobs, False


class ZhaopinPublicAdapter:
    """Polite SSR adapter for publicly accessible Zhaopin search pages."""

    source_name = "zhaopin"

    def __init__(
        self,
        *,
        cities: Sequence[tuple[str, str]] = DEFAULT_ZHAOPIN_CITIES,
        keywords: Sequence[str] = DEFAULT_ZHAOPIN_KEYWORDS,
        max_pages: int = 1,
        exclude_social: bool = True,
        request_interval: float = 0.6,
    ) -> None:
        self.cities = list(cities)
        self.keywords = list(keywords)
        self.max_pages = max(1, max_pages)
        self.exclude_social = exclude_social
        self.request_interval = request_interval
        self.errors: list[str] = []
        self.gated = False

    def fetch_jobs(self) -> Iterator[dict[str, Any]]:
        seen_hashes: set[str] = set()
        with httpx.Client(
            headers=_HEADERS,
            timeout=12.0,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            for jl_code, city_name in self.cities:
                if self.gated:
                    break
                for kw in self.keywords:
                    if self.gated:
                        break
                    for page in range(1, self.max_pages + 1):
                        if self.request_interval > 0:
                            time.sleep(self.request_interval)
                        url = (
                            f"https://www.zhaopin.com/jobs/"
                            f"?jl={jl_code}&kw={quote(kw)}&p={page}"
                        )
                        try:
                            resp = client.get(url)
                            resp.raise_for_status()
                        except httpx.HTTPError as exc:
                            self.errors.append(f"zhaopin {city_name}/{kw}/p{page}: {exc}")
                            break

                        jobs, gated = parse_zhaopin_html(
                            resp.text,
                            exclude_social=self.exclude_social,
                            final_url=str(resp.url),
                        )
                        if gated:
                            self.gated = True
                            self.errors.append(
                                f"zhaopin gated at {city_name}/{kw}/p{page}; "
                                "stopped politely (use collect-browser)"
                            )
                            break
                        if not jobs:
                            break
                        for job in jobs:
                            dh = job["dedup_hash"]
                            if dh not in seen_hashes:
                                seen_hashes.add(dh)
                                yield job

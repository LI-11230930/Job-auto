"""Base contracts, normalization, and deduplication helpers for job sources."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from typing import Any, Protocol

DEFAULT_ALLOWED_SCHOOLS: tuple[str, ...] = ()

OPEN_PUBLIC_NCSS_SOURCES: tuple[str, ...] = (
    "国家大学生就业服务平台",
    "智联招聘",
    "前程无忧",
    "国聘",
    "猎聘",
    "boss直聘",
    "51job",
    "应届生求职网",
    "牛客",
)

_SSO_LOGIN_URL_HINTS: tuple[str, ...] = (
    "cas/login",
    "/cas/",
    "authserver.",
    "://ids.",
    "unifiedidentity",
    "sso/login",
)


def is_restricted_university_portal(
    *,
    source: str | None = "",
    url: str | None = "",
    jd_text: str | None = "",
    apply_channel: str | None = "",
    apply_target: str | None = "",
    allowed_schools: Sequence[str] = DEFAULT_ALLOWED_SCHOOLS,
) -> tuple[bool, str]:
    """Detect closed campus/provincial SSO channels inaccessible to outside students."""
    channel = (apply_channel or "").strip().lower()
    target = (apply_target or "").strip()
    raw_url = (url or target).strip()
    lower_url = raw_url.lower()
    src = (source or "").strip().lower()
    jd = str(jd_text or "")

    # Direct email or verified non-campus external company portal is always usable.
    if channel == "email" or ("@" in target and not target.lower().startswith("http")):
        return False, ""
    if channel == "company_portal" and raw_url and "ncss.cn" not in lower_url and ".edu.cn" not in lower_url:
        return False, ""

    if any(hint in lower_url for hint in _SSO_LOGIN_URL_HINTS) and not any(
        s and s in raw_url for s in allowed_schools
    ):
        return True, "统一身份认证登录链接"

    if (
        ".edu.cn" in lower_url
        and not any(s in jd for s in allowed_schools if s)
        and not any(s in raw_url for s in allowed_schools if s)
    ):
        return True, "外校就业网域名"

    if src == "ncss" or "ncss.cn" in lower_url:
        m = re.search(r"【来源高校/站点】([^\r\n]+)", jd)
        if m:
            origin_site = m.group(1).strip()
            origin_low = origin_site.lower()
            is_open_public = any(tok in origin_low for tok in OPEN_PUBLIC_NCSS_SOURCES)
            is_own_school = any(s and s in origin_site for s in allowed_schools)
            if origin_site and not is_open_public and not is_own_school:
                return True, f"需「{origin_site}」统一身份认证"

    return False, ""

CHANNEL_PRIORITY = {
    "company_portal": 30,
    "email": 20,
    "third_party": 10,
    "unknown": 0,
}


class JobSourceAdapter(Protocol):
    source_name: str

    def fetch_jobs(self) -> Iterable[dict[str, Any]]:
        """Yield normalized job dictionaries ready for Database.upsert_jobs."""


def normalize_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[\s\-_()（）【】\[\]·/]+", "", text)
    return text


def split_cities(raw_location: str | None) -> list[str]:
    if not raw_location:
        return []
    parts = re.split(r"[,，、;/|\s]+", raw_location.strip())
    cleaned = [p.strip() for p in parts if p.strip() and p.strip() not in {"全国", "不限"}]
    if not cleaned and raw_location.strip():
        return [raw_location.strip()]
    return list(dict.fromkeys(cleaned))


def infer_channel(apply_url: str, email: str, source: str) -> tuple[str, str, int]:
    url = (apply_url or "").strip()
    mail = (email or "").strip()
    src = (source or "").strip().lower()

    aggregator_domains = (
        "givemeoc.com",
        "deepoffer.cn",
        "nowcoder.com",
        "shixiseng.com",
        "ncss.cn",
        "zhaopin.com",
        "zhipin.com",
        "51job.com",
        "iguopin.com",
    )
    if mail and (not url or any(dom in url.lower() for dom in aggregator_domains)):
        return "email", mail, CHANNEL_PRIORITY["email"]

    if url:
        if (
            any(dom in url.lower() for dom in aggregator_domains)
            or src
            in {
                "givemeoc",
                "deepoffer",
                "deepoffer_csv",
                "niuke",
                "shixiseng",
                "ncss",
                "zhaopin",
                "zhipin",
                "51job",
                "iguopin",
            }
            and "careers." not in url.lower()
            and "beisen" not in url.lower()
            and "moka" not in url.lower()
        ):
            return "third_party", url, CHANNEL_PRIORITY["third_party"]
        return "company_portal", url, CHANNEL_PRIORITY["company_portal"]

    if mail:
        return "email", mail, CHANNEL_PRIORITY["email"]

    return "unknown", "", CHANNEL_PRIORITY["unknown"]


def compute_dedup_hash(
    *,
    company: str,
    title: str,
    job_type: str,
    official_req_id: str = "",
) -> str:
    comp = normalize_text(company)
    ttl = normalize_text(title)
    jtype = normalize_text(job_type)
    # Strip trailing city suffixes sometimes appended to titles like "-上海"
    key = f"{comp}|{ttl}|{jtype}|{official_req_id.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]

"""Local HTML / JSON snapshot importer for Boss直聘, 前程无忧, 国聘网, 智联招聘, 实习僧."""

from __future__ import annotations

import html as _html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .base import compute_dedup_hash, infer_channel, split_cities
from .ncss import parse_ncss_payload
from .shixiseng import parse_shixiseng_html
from .zhaopin_public import parse_zhaopin_html

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(fragment: str) -> str:
    text = _html.unescape(_TAG_RE.sub(" ", fragment or ""))
    return " ".join(text.split())


def _infer_job_type(title: str, hint: str = "", default: str = "校招") -> str:
    joined = f"{title} {hint}"
    if "实习" in joined:
        return "实习"
    if any(k in joined for k in ("校招", "校园", "应届", "27届", "2027", "管培")):
        return "校招"
    if any(exp in hint for exp in ("1-3年", "3-5年", "5-10年", "10年以上")):
        return "社招"
    return default


def _build_job(
    *,
    source: str,
    company: str,
    title: str,
    city_raw: str = "",
    url: str = "",
    job_type_hint: str = "",
    jd_text: str = "",
    source_job_id: str = "",
    industry: str = "",
    exclude_social: bool = True,
) -> dict[str, Any] | None:
    company_clean = company.strip()
    title_clean = title.strip()
    if not company_clean or not title_clean:
        return None
    job_type = _infer_job_type(title_clean, job_type_hint)
    if exclude_social and job_type == "社招":
        return None
    apply_channel, apply_target, priority_rank = infer_channel(url, "", source)
    return {
        "source": source,
        "source_job_id": source_job_id or url,
        "company": company_clean,
        "title": title_clean,
        "cities": split_cities(city_raw),
        "job_type": job_type,
        "jd_text": jd_text.strip(),
        "url": url.strip(),
        "apply_channel": apply_channel,
        "apply_target": apply_target,
        "deadline": "",
        "industry": industry.strip(),
        "status": "active",
        "dedup_hash": compute_dedup_hash(
            company=company_clean,
            title=title_clean,
            job_type=job_type,
            official_req_id="",
        ),
        "priority_rank": priority_rank,
    }


def _detect_site(text: str, filename_hint: str = "") -> str:
    low = (text[:6000] + " " + filename_hint).lower()
    if (
        "zhaopin" in low
        or "position-card__job-name" in text
        or "joblist-box__item" in text
        or ("__initial_state__" in low and "positionlist" in text)
    ):
        return "zhaopin"
    if "data-intern-id=" in text or "shixiseng" in low:
        return "shixiseng"
    if "job-card-wrapper" in text or "job-card-box" in text or "zhipin.com" in low or "boss" in low:
        return "zhipin"
    if "j_joblist" in text or "51job" in low or "window.__app_initial_state__" in low:
        return "51job"
    if "iguopin" in low or "国聘" in text[:4000]:
        return "iguopin"
    if "ncss.cn" in low:
        return "ncss"
    return "generic"


def _extract_zhipin_html(html_text: str, *, exclude_social: bool = True) -> list[dict[str, Any]]:
    # Split on Boss直聘 card wrappers (<li class="job-card-wrapper"> or <li class="job-card-box">)
    blocks = re.split(r'<li[^>]*class="[^"]*job-card-(?:wrapper|box)[^"]*"[^>]*>', html_text)
    if len(blocks) < 2:
        blocks = re.split(r'<div[^>]*class="[^"]*job-card-body[^"]*"[^>]*>', html_text)
    jobs: list[dict[str, Any]] = []
    for block in blocks[1:]:
        chunk = block[:6500]
        href_m = re.search(r'href="([^"]*job_detail[^"]*)"', chunk)
        url = urljoin("https://www.zhipin.com", href_m.group(1)) if href_m else ""
        title_m = re.search(r'class="[^"]*job-(?:name|title)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        comp_m = re.search(
            r'class="[^"]*(?:company-name|boss-name)[^"]*"[^>]*>(.*?)</(?:a|h3|span|div)',
            chunk,
            re.DOTALL,
        )
        if not comp_m:
            comp_m = re.search(r'<h3[^>]*class="[^"]*company-name[^"]*"[^>]*>(.*?)</h3>', chunk, re.DOTALL)
        city_m = re.search(
            r'class="[^"]*(?:job-area|company-location)[^"]*"[^>]*>(.*?)</(?:span|div)',
            chunk,
            re.DOTALL,
        )
        sal_m = re.search(
            r'class="[^"]*(?:job-salary|salary)[^"]*"[^>]*>(.*?)</(?:span|div)',
            chunk,
            re.DOTALL,
        )
        tags_m = re.findall(r'<li[^>]*>(.*?)</li>', chunk[:3500], re.DOTALL)
        tags = [_strip_tags(t) for t in tags_m if _strip_tags(t)][:8]
        title = _strip_tags(title_m.group(1)) if title_m else ""
        company = _strip_tags(comp_m.group(1)) if comp_m else ""
        city_raw = _strip_tags(city_m.group(1)) if city_m else ""
        salary = _strip_tags(sal_m.group(1)) if sal_m else ""
        hint = " ".join(tags)
        jd_lines = ["【来源平台】Boss直聘"]
        if salary:
            jd_lines.append(f"【薪资范围】{salary}")
        if city_raw:
            jd_lines.append(f"【工作地点】{city_raw}")
        if tags:
            jd_lines.append(f"【要求标签】{'、'.join(tags)}")
        job = _build_job(
            source="zhipin",
            company=company,
            title=title,
            city_raw=city_raw,
            url=url,
            job_type_hint=hint,
            jd_text="\n".join(jd_lines),
            exclude_social=exclude_social,
        )
        if job:
            jobs.append(job)
    return jobs


def _extract_51job_html(html_text: str, *, exclude_social: bool = True) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    # Path A: 51job card blocks (<div class="joblist-item"> or <div class="e">)
    card_splits = re.split(
        r'<div[^>]*class="[^"]*(?:joblist-item|e\b[^"]*job)[^"]*"[^>]*>',
        html_text,
    )
    if len(card_splits) < 2:
        card_splits = re.split(r'<div[^>]*sensorsname="JobSearch"[^>]*>', html_text)
    for block in card_splits[1:]:
        chunk = block[:6000]
        title_m = re.search(
            r'class="[^"]*(?:jname|job-name|t)[^"]*"[^>]*title="([^"]+)"', chunk
        ) or re.search(r'class="[^"]*(?:jname|job-name)[^"]*"[^>]*>(.*?)</a>', chunk, re.DOTALL)
        comp_m = re.search(
            r'class="[^"]*(?:cname|comp-name)[^"]*"[^>]*title="([^"]+)"', chunk
        ) or re.search(r'class="[^"]*(?:cname|comp-name)[^"]*"[^>]*>(.*?)</a>', chunk, re.DOTALL)
        city_m = re.search(r'class="[^"]*(?:area|d at|city)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        sal_m = re.search(r'class="[^"]*(?:sal|salary)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        href_m = re.search(r'href="(https?://[^"]*51job\.com/[^"]+)"', chunk)

        title = _strip_tags(title_m.group(1)) if title_m else ""
        company = _strip_tags(comp_m.group(1)) if comp_m else ""
        city_raw = _strip_tags(city_m.group(1)) if city_m else ""
        salary = _strip_tags(sal_m.group(1)) if sal_m else ""
        url = href_m.group(1).strip() if href_m else ""

        jd_lines = ["【来源平台】前程无忧 51job"]
        if salary:
            jd_lines.append(f"【薪资范围】{salary}")
        if city_raw:
            jd_lines.append(f"【工作地点】{city_raw}")
        job = _build_job(
            source="51job",
            company=company,
            title=title,
            city_raw=city_raw,
            url=url,
            jd_text="\n".join(jd_lines),
            exclude_social=exclude_social,
        )
        if job:
            jobs.append(job)
    return jobs


def _extract_iguopin_html(html_text: str, *, exclude_social: bool = True) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    # Match links to iguopin job details + surrounding card content
    for m in re.finditer(r'href="([^"]*/job/detail/[^"]+)"', html_text):
        url = urljoin("https://www.iguopin.com", m.group(1))
        start = max(0, m.start() - 500)
        end = min(len(html_text), m.end() + 2500)
        chunk = html_text[start:end]
        title_m = re.search(
            r'class="[^"]*(?:job-name|title|position-name)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
        )
        comp_m = re.search(
            r'class="[^"]*(?:company-name|corp-name|org-name)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
        )
        city_m = re.search(
            r'class="[^"]*(?:city|district|location|area)[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
        )
        title = _strip_tags(title_m.group(1)) if title_m else ""
        company = _strip_tags(comp_m.group(1)) if comp_m else ""
        city_raw = _strip_tags(city_m.group(1)) if city_m else ""
        job = _build_job(
            source="iguopin",
            company=company,
            title=title,
            city_raw=city_raw,
            url=url,
            jd_text=f"【来源平台】国聘网\n【工作地点】{city_raw or '见详情页'}",
            exclude_social=exclude_social,
        )
        if job:
            jobs.append(job)
    return jobs


def _extract_json_payload(
    raw_text: str,
    *,
    site: str,
    exclude_social: bool = True,
) -> list[dict[str, Any]]:
    data = json.loads(raw_text)
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        # Could be NCSS or Iguopin API JSON saved via DevTools
        inner = data["data"]
        lst = inner.get("list") or inner.get("records") or []
        if lst and isinstance(lst, list):
            if "recName" in lst[0] and "jobId" in lst[0]:
                return parse_ncss_payload(data)
            jobs: list[dict[str, Any]] = []
            for item in lst:
                if not isinstance(item, dict):
                    continue
                company = str(
                    item.get("company_name")
                    or item.get("companyName")
                    or item.get("corpName")
                    or ""
                ).strip()
                title = str(
                    item.get("job_name") or item.get("jobName") or item.get("title") or ""
                ).strip()
                city = str(
                    item.get("district_names")
                    or item.get("workCity")
                    or item.get("city")
                    or ""
                ).strip()
                jid = str(item.get("id") or item.get("job_id") or "").strip()
                url = str(item.get("url") or "").strip()
                if not url and jid and site == "iguopin":
                    url = f"https://www.iguopin.com/job/detail/{jid}"
                job = _build_job(
                    source=site if site != "auto" else "iguopin",
                    company=company,
                    title=title,
                    city_raw=city,
                    url=url,
                    jd_text=str(item.get("description") or item.get("jobSummary") or ""),
                    source_job_id=jid,
                    exclude_social=exclude_social,
                )
                if job:
                    jobs.append(job)
            return jobs
    return []


def _extract_zhaopin_dom_html(html_text: str, *, exclude_social: bool = True) -> list[dict[str, Any]]:
    """Extract jobs from both Zhaopin SSR (__INITIAL_STATE__) and logged-in Vue SPA DOM."""
    ssr_jobs, _ = parse_zhaopin_html(html_text, exclude_social=exclude_social)
    if ssr_jobs:
        return ssr_jobs

    jobs: list[dict[str, Any]] = []
    # Pattern A: Zhaopin Campus / Home Recommend SPA (.position-list__item / .position-card)
    card_blocks = re.split(r'<div[^>]*class="[^"]*position-list__item[^"]*"[^>]*>', html_text)
    if len(card_blocks) > 1:
        for block in card_blocks[1:]:
            chunk = block[:6500]
            title_m = re.search(
                r'class="[^"]*position-card__job-name[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
            )
            city_m = re.search(
                r'class="[^"]*position-card__city-name[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
            )
            sal_m = re.search(
                r'class="[^"]*position-card__salary[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
            )
            comp_m = re.search(
                r'class="[^"]*position-card__company__name[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
            )
            tags = [
                _strip_tags(t)
                for t in re.findall(
                    r'class="[^"]*position-card__tags__item[^"]*"[^>]*>(.*?)</',
                    chunk,
                    re.DOTALL,
                )
                if _strip_tags(t)
            ]
            ind_m = re.search(
                r'class="[^"]*position-card__company__tabs-item[^"]*"[^>]*>(.*?)</',
                chunk,
                re.DOTALL,
            )
            jdno_m = re.search(r'(?:&quot;|")jdno(?:&quot;|")\s*:\s*(?:&quot;|")([A-Za-z0-9_]+)', chunk)
            jdno = jdno_m.group(1) if jdno_m else ""
            url = f"https://jobs.zhaopin.com/{jdno}.htm" if jdno else ""

            title = _strip_tags(title_m.group(1)) if title_m else ""
            company = _strip_tags(comp_m.group(1)) if comp_m else ""
            city_raw = _strip_tags(city_m.group(1)).strip("「」[]() ") if city_m else ""
            salary = _strip_tags(sal_m.group(1)) if sal_m else ""
            industry = _strip_tags(ind_m.group(1)) if ind_m else ""

            jd_lines = ["【来源平台】智联招聘"]
            if salary:
                jd_lines.append(f"【薪资范围】{salary}")
            if city_raw:
                jd_lines.append(f"【工作地点】{city_raw}")
            if tags:
                jd_lines.append(f"【要求标签】{'、'.join(tags)}")
            job = _build_job(
                source="zhaopin",
                company=company,
                title=title,
                city_raw=city_raw,
                url=url,
                source_job_id=jdno,
                industry=industry,
                job_type_hint=" ".join(tags),
                jd_text="\n".join(jd_lines),
                exclude_social=exclude_social,
            )
            if job:
                jobs.append(job)
        if jobs:
            return jobs

    # Pattern B: Zhaopin Search Results SPA (sou.zhaopin.com .joblist-box__item)
    sou_blocks = re.split(r'<div[^>]*class="[^"]*joblist-box__item[^"]*"[^>]*>', html_text)
    for block in sou_blocks[1:]:
        chunk = block[:6500]
        href_m = re.search(r'href="(https?://[^"]*zhaopin\.com/[^"]+)"', chunk)
        url = href_m.group(1) if href_m else ""
        title_m = re.search(r'class="[^"]*jobinfo__name[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        comp_m = re.search(r'class="[^"]*companyinfo__name[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        sal_m = re.search(r'class="[^"]*jobinfo__salary[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL)
        other_items = [
            _strip_tags(x)
            for x in re.findall(
                r'class="[^"]*jobinfo__other-info-item[^"]*"[^>]*>(.*?)</', chunk, re.DOTALL
            )
            if _strip_tags(x)
        ]
        city_raw = other_items[0] if other_items else ""
        hint = " ".join(other_items[1:])
        title = _strip_tags(title_m.group(1)) if title_m else ""
        company = _strip_tags(comp_m.group(1)) if comp_m else ""
        salary = _strip_tags(sal_m.group(1)) if sal_m else ""
        jd_lines = ["【来源平台】智联招聘"]
        if salary:
            jd_lines.append(f"【薪资范围】{salary}")
        if city_raw:
            jd_lines.append(f"【工作地点】{city_raw}")
        if other_items:
            jd_lines.append(f"【要求标签】{'、'.join(other_items)}")
        job = _build_job(
            source="zhaopin",
            company=company,
            title=title,
            city_raw=city_raw,
            url=url,
            job_type_hint=hint,
            jd_text="\n".join(jd_lines),
            exclude_social=exclude_social,
        )
        if job:
            jobs.append(job)
    return jobs


def extract_jobs_from_snapshot(
    content: str,
    *,
    site: str = "auto",
    filename_hint: str = "",
    exclude_social: bool = True,
) -> list[dict[str, Any]]:
    """Extract normalized jobs from a saved HTML or JSON page snapshot."""
    stripped = content.lstrip()
    chosen_site = site if site != "auto" else _detect_site(content, filename_hint=filename_hint)
    if stripped.startswith(("{", "[")):
        try:
            parsed = _extract_json_payload(content, site=chosen_site, exclude_social=exclude_social)
            if parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    if chosen_site == "zhaopin":
        return _extract_zhaopin_dom_html(content, exclude_social=exclude_social)
    if chosen_site == "shixiseng":
        return parse_shixiseng_html(content)
    if chosen_site == "zhipin":
        return _extract_zhipin_html(content, exclude_social=exclude_social)
    if chosen_site == "51job":
        return _extract_51job_html(content, exclude_social=exclude_social)
    if chosen_site == "iguopin":
        return _extract_iguopin_html(content, exclude_social=exclude_social)

    # Fallback: try each known HTML extractor until one matches
    for extractor in (
        lambda c: _extract_zhaopin_dom_html(c, exclude_social=exclude_social),
        parse_shixiseng_html,
        lambda c: _extract_zhipin_html(c, exclude_social=exclude_social),
        lambda c: _extract_51job_html(c, exclude_social=exclude_social),
        lambda c: _extract_iguopin_html(c, exclude_social=exclude_social),
    ):
        found = extractor(content)
        if found:
            return found
    return []


def import_snapshot_path(
    target_path: Path,
    *,
    site: str = "auto",
    exclude_social: bool = True,
) -> list[dict[str, Any]]:
    """Read a single file or recursively read *.html/*.htm/*.json in a directory."""
    files = (
        [target_path]
        if target_path.is_file()
        else sorted(
            p
            for p in target_path.rglob("*")
            if p.is_file() and p.suffix.lower() in {".html", ".htm", ".json"}
        )
    )
    dedup: dict[str, dict[str, Any]] = {}
    for file_path in files:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
        for job in extract_jobs_from_snapshot(
            raw,
            site=site,
            filename_hint=file_path.name,
            exclude_social=exclude_social,
        ):
            dedup.setdefault(job["dedup_hash"], job)
    return list(dedup.values())

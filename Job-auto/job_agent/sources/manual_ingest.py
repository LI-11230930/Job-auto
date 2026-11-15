"""Manual JD ingestion: single JD entry and LLM-powered multi-JD splitting (Stage 1.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm.base import LLMProvider, load_prompt_asset
from .base import CHANNEL_PRIORITY, compute_dedup_hash, split_cities


def build_manual_job(
    *,
    company: str,
    title: str,
    jd_text: str,
    cities: list[str] | str = "",
    job_type: str = "校招",
    url: str = "",
    email: str = "",
    deadline: str = "",
    industry: str = "",
) -> dict[str, Any]:
    city_list = split_cities(cities) if isinstance(cities, str) else list(dict.fromkeys(cities))
    if url.strip():
        channel = "company_portal"
        target = url.strip()
        rank = CHANNEL_PRIORITY["company_portal"]
    elif email.strip():
        channel = "email"
        target = email.strip()
        rank = CHANNEL_PRIORITY["email"]
    else:
        channel = "unknown"
        target = ""
        rank = CHANNEL_PRIORITY["unknown"]

    return {
        "source": "manual_paste",
        "source_job_id": "",
        "company": company.strip(),
        "title": title.strip(),
        "cities": city_list,
        "job_type": job_type.strip() or "校招",
        "jd_text": jd_text.strip(),
        "url": url.strip(),
        "apply_channel": channel,
        "apply_target": target,
        "deadline": deadline.strip(),
        "industry": industry.strip(),
        "status": "active",
        "dedup_hash": compute_dedup_hash(
            company=company,
            title=title,
            job_type=job_type,
        ),
        "priority_rank": rank,
    }


def split_summary_post(
    *,
    raw_text: str,
    llm: LLMProvider,
    prompts_root: Path,
    model_override: str | None = None,
) -> list[dict[str, Any]]:
    asset = load_prompt_asset(prompts_root, "jd_split")
    result = llm.generate_json(
        asset=asset,
        payload={"raw_text": raw_text},
        model_override=model_override,
    )
    jobs_out: list[dict[str, Any]] = []
    for row in result.get("jobs", []):
        company = str(row.get("company") or "").strip()
        title = str(row.get("title") or "").strip()
        if not company or not title:
            continue
        target = str(row.get("apply_target") or "").strip()
        is_email = "@" in target and not target.startswith("http")
        jobs_out.append(
            build_manual_job(
                company=company,
                title=title,
                jd_text=str(row.get("jd_text") or ""),
                cities=list(row.get("cities") or []),
                job_type=str(row.get("job_type") or "校招"),
                url="" if is_email else target,
                email=target if is_email else "",
                deadline=str(row.get("deadline") or ""),
            )
        )
    return jobs_out

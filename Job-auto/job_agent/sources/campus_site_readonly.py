"""Read-only adapter for optional local campus jobs.json feed."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .base import compute_dedup_hash, infer_channel, split_cities

OFFICIAL_CAREER_SOURCES = {"tencent_careers", "netease_careers", "company_careers"}
CAMPUS_BATCHES = {"秋招", "春招", "校招", "校园招聘"}


def _map_job_type(batch: str) -> str:
    b = (batch or "").strip()
    if any(k in b for k in ("秋招", "春招", "校招", "管培")):
        return "校招"
    if "实习" in b:
        return "实习"
    if "社招" in b:
        return "社招"
    return "未知"


def _map_status(raw_status: str) -> str:
    s = (raw_status or "").strip()
    if s in {"已结束", "已截止", "过期", "expired", "closed"}:
        return "expired"
    return "active"


class CampusSiteReadonlyAdapter:
    """Strictly read-only reader for the existing 校招网站 jobs.json."""

    source_name = "campus_site_readonly"

    def __init__(self, jobs_json_path: str | Path, *, exclude_social: bool = False) -> None:
        self.jobs_json_path = Path(jobs_json_path)
        self.exclude_social = exclude_social

    def fetch_jobs(self) -> Iterator[dict[str, Any]]:
        if not self.jobs_json_path.exists():
            raise FileNotFoundError(f"Campus site jobs.json not found: {self.jobs_json_path}")

        with self.jobs_json_path.open("r", encoding="utf-8") as fh:
            raw_items = json.load(fh)

        if not isinstance(raw_items, list):
            raise TypeError("Expected JSON list in campus site jobs.json")

        for row in raw_items:
            if not isinstance(row, dict):
                continue
            src = str(row.get("source") or "").strip()
            if src == "内置示例":
                continue

            company = str(row.get("company") or "").strip()
            title = str(row.get("position") or row.get("title") or "").strip()
            if not company or not title:
                continue

            job_type = _map_job_type(str(row.get("batch") or ""))
            if self.exclude_social and job_type == "社招":
                continue

            apply_url = str(row.get("apply_url") or row.get("announce_url") or "").strip()
            email = str(row.get("email") or "").strip()
            apply_channel, apply_target, priority_rank = infer_channel(apply_url, email, src)

            desc = str(row.get("description") or "").strip()
            reqs = str(row.get("requirements") or "").strip()
            jd_parts = []
            if desc:
                jd_parts.append(f"【岗位职责】\n{desc}")
            if reqs:
                jd_parts.append(f"【任职要求】\n{reqs}")
            target_grad = str(row.get("target_graduation") or "").strip()
            if target_grad:
                jd_parts.append(f"【面向届别】{target_grad}")

            source_id = str(row.get("source_id") or "").strip()
            official_req_id = source_id if src in OFFICIAL_CAREER_SOURCES else ""

            yield {
                "source": f"campus_site:{src or 'unknown'}",
                "source_job_id": str(row.get("id") or source_id),
                "company": company,
                "title": title,
                "cities": split_cities(str(row.get("location") or "")),
                "job_type": job_type,
                "jd_text": "\n\n".join(jd_parts),
                "url": apply_url,
                "apply_channel": apply_channel,
                "apply_target": apply_target,
                "deadline": str(row.get("deadline") or "").strip(),
                "industry": str(row.get("industry") or "").strip(),
                "status": _map_status(str(row.get("status") or "")),
                "dedup_hash": compute_dedup_hash(
                    company=company,
                    title=title,
                    job_type=job_type,
                    official_req_id=official_req_id,
                ),
                "priority_rank": priority_rank,
            }

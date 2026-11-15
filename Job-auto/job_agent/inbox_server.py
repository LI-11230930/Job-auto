"""Localhost HTTP receiver for the Edge/Chrome Companion Collector Extension.

Why this exists:
- Portals like Boss直聘 enforce anti-automation checks (`navigator.webdriver`) that cause
  Playwright-launched browsers to redirect/navigate back in a loop.
- By browsing in your normal, non-automated Edge window and clicking the local companion
  extension button, page HTML / visible cards are POSTed directly to 127.0.0.1:8765,
  parsed into normalized jobs, upserted into SQLite, and reflected in local/progress.html.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import Database
from .progress import update_progress_artifacts
from .sources.base import compute_dedup_hash, infer_channel, split_cities
from .sources.html_import import _infer_job_type, extract_jobs_from_snapshot

logger = logging.getLogger(__name__)


class IngestPageRequest(BaseModel):
    url: str = ""
    site: str = "auto"
    html: str = ""
    cards: list[dict[str, Any]] = Field(default_factory=list)
    exclude_social: bool = True


def resolve_site_from_url(url: str, explicit_site: str = "auto") -> str:
    if explicit_site and explicit_site != "auto":
        return explicit_site.strip().lower()
    low = (url or "").lower()
    if "zhipin.com" in low:
        return "zhipin"
    if "51job.com" in low:
        return "51job"
    if "zhaopin.com" in low:
        return "zhaopin"
    if "iguopin.com" in low:
        return "iguopin"
    if "shixiseng.com" in low:
        return "shixiseng"
    if "ncss.cn" in low:
        return "ncss"
    return "auto"


def _normalize_dom_cards(
    cards: list[dict[str, Any]],
    *,
    site: str,
    exclude_social: bool,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    source_name = site if site != "auto" else "browser"
    for row in cards:
        title = str(row.get("title") or "").strip()
        company = str(row.get("company") or "").strip()
        if not title or not company:
            continue
        city_raw = str(row.get("city") or "").strip()
        salary = str(row.get("salary") or "").strip()
        tags = [str(t).strip() for t in (row.get("tags") or []) if str(t).strip()]
        url = str(row.get("url") or "").strip()
        job_type = _infer_job_type(title, " ".join(tags))
        if exclude_social and job_type == "社招":
            continue
        apply_channel, apply_target, priority_rank = infer_channel(url, "", source_name)
        jd_parts = [f"【来源平台】{source_name}"]
        if salary:
            jd_parts.append(f"【薪资范围】{salary}")
        if city_raw:
            jd_parts.append(f"【工作地点】{city_raw}")
        if tags:
            jd_parts.append(f"【要求标签】{'、'.join(tags)}")
        normalized.append(
            {
                "source": source_name,
                "source_job_id": url,
                "company": company,
                "title": title,
                "cities": split_cities(city_raw),
                "job_type": job_type,
                "jd_text": "\n".join(jd_parts),
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
    return normalized


def get_inbox_health(db_path: Path) -> dict[str, Any]:
    """Return database readiness and current job count for extension popup checks."""
    db = Database(db_path)
    db.init_schema()
    return {
        "status": "ok",
        "total_in_db": db.count_jobs(),
        "db_path": str(db_path),
    }


def ingest_extension_page(
    req: IngestPageRequest,
    *,
    db_path: Path,
    inbox_dir: Path | None = None,
    refresh_progress: bool = True,
) -> dict[str, Any]:
    """Normalize and persist jobs captured by the browser collector extension."""
    resolved_inbox = inbox_dir or (db_path.parent / "inbox")
    resolved_site = resolve_site_from_url(req.url, req.site)
    site_folder = resolved_site if resolved_site != "auto" else "manual"
    snapshot_path = ""

    jobs_map: dict[str, dict[str, Any]] = {}
    if req.cards:
        for item in _normalize_dom_cards(
            req.cards, site=resolved_site, exclude_social=req.exclude_social
        ):
            jobs_map[item["dedup_hash"]] = item

    if req.html.strip():
        target_dir = resolved_inbox / site_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snap = target_dir / f"ext_{stamp}.html"
        snap.write_text(req.html, encoding="utf-8")
        snapshot_path = str(snap)

        for item in extract_jobs_from_snapshot(
            req.html,
            site=resolved_site,
            filename_hint=req.url,
            exclude_social=req.exclude_social,
        ):
            jobs_map.setdefault(item["dedup_hash"], item)

    extracted = list(jobs_map.values())
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run(run_type=f"extension:{site_folder}")
    counts = db.upsert_jobs(extracted)
    summary = {"extracted": len(extracted), **counts}
    db.finish_run(run_id, status="completed", stats=summary)
    total_in_db = db.count_jobs()

    if refresh_progress and len(extracted) > 0:
        try:
            update_progress_artifacts(db_path=db_path)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to refresh progress artifacts: %s", exc)

    return {
        "status": "ok",
        "site": site_folder,
        **summary,
        "total_in_db": total_in_db,
        "snapshot_path": snapshot_path,
    }


def create_inbox_app(
    *,
    db_path: Path,
    inbox_dir: Path | None = None,
    refresh_progress: bool = True,
) -> FastAPI:
    app = FastAPI(title="Job-Auto Local Inbox Receiver", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    resolved_inbox = inbox_dir or (db_path.parent / "inbox")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return get_inbox_health(db_path)

    @app.post("/api/ingest-page")
    def ingest_page(req: IngestPageRequest) -> dict[str, Any]:
        return ingest_extension_page(
            req,
            db_path=db_path,
            inbox_dir=resolved_inbox,
            refresh_progress=refresh_progress,
        )

    return app

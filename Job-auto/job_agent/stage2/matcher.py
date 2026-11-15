"""Stage 2.2: AI job match scoring using sanitized MasterProfile and Job-auto prompts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import UserConfig
from ..db import Database
from ..llm.base import LLMProvider, load_prompt_asset
from ..master import MasterProfile


def build_candidate_match_payload(profile: MasterProfile, cfg: UserConfig) -> dict[str, Any]:
    """Build a strictly secret-free candidate summary for LLM matching."""
    eng = cfg.profile.english_status
    return {
        "education": profile.education.model_dump(),
        "certifications": list(profile.certifications),
        "skills": [s.model_dump() for s in profile.skills],
        "english_status": {
            "cet4_passed": eng.cet4_passed,
            "cet4_best_score": eng.cet4_best_score,
            "cet6_passed": eng.cet6_passed,
            "gaokao_english": eng.gaokao_english,
        },
        "target_job_types": list(cfg.preferences.target_job_types),
        "primary_cities": list(cfg.preferences.primary_cities),
        "secondary_cities": list(cfg.preferences.secondary_cities),
        "intern_availability": cfg.profile.intern_availability,
        "experiences": [
            {
                "id": exp.id,
                "category": exp.category,
                "organization": exp.organization,
                "role": exp.role,
                "period": exp.period,
                "bullets": [{"id": b.id, "text": b.text, "tags": b.tags} for b in exp.bullets],
            }
            for exp in profile.experiences
        ],
    }


def score_single_job(
    *,
    job: dict[str, Any],
    profile: MasterProfile,
    cfg: UserConfig,
    llm: LLMProvider,
    prompts_root: Path,
    model_override: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    """Score one job via LLMProvider and return (result_dict, model_used, prompt_version)."""
    asset = load_prompt_asset(prompts_root, "job_match")
    cities = job.get("cities")
    if cities is None and "cities_json" in job:
        try:
            cities = json.loads(job["cities_json"] or "[]")
        except json.JSONDecodeError:
            cities = []

    payload = {
        "weights": cfg.scoring.weights.model_dump(),
        "candidate": build_candidate_match_payload(profile, cfg),
        "job": {
            "id": job.get("id"),
            "company": job.get("company"),
            "title": job.get("title"),
            "cities": cities or [],
            "job_type": job.get("job_type"),
            "industry": job.get("industry", ""),
            "deadline": job.get("deadline", ""),
            "jd_text": (job.get("jd_text") or "")[:3500],
        },
    }
    model_used = model_override or cfg.llm.default_model or asset.recommended_model
    result = llm.generate_json(asset=asset, payload=payload, model_override=model_used)
    return result, model_used, asset.prompt_version


def run_match_batch(
    *,
    db: Database,
    cfg: UserConfig,
    llm: LLMProvider,
    prompts_root: Path,
    candidates: list[dict[str, Any]],
    master_version_id: int,
    profile: MasterProfile,
    rescore: bool = False,
) -> dict[str, Any]:
    """Score a batch of prefiltered jobs and persist results to `matches`."""
    scored = 0
    skipped_existing = 0
    errors = 0
    high_score_ids: list[int] = []
    min_score = cfg.scoring.min_score_for_package

    with db.connect() as conn:
        existing_pairs = {
            (int(r["job_id"]), int(r["master_version_id"]))
            for r in conn.execute("SELECT job_id, master_version_id FROM matches").fetchall()
        }

    for job in candidates:
        job_id = int(job["id"])
        if not rescore and (job_id, master_version_id) in existing_pairs:
            skipped_existing += 1
            continue
        try:
            result, model_used, prompt_ver = score_single_job(
                job=job,
                profile=profile,
                cfg=cfg,
                llm=llm,
                prompts_root=prompts_root,
            )
            score = int(result.get("score") or 0) if result.get("hard_filter_pass", True) else 0
            match_id = db.insert_match(
                job_id=job_id,
                master_version_id=master_version_id,
                rule_pass=bool(result.get("hard_filter_pass", True)),
                score=score,
                reasons=result.get("reasons") or [],
                gaps=result.get("gaps") or [],
                strategy=result.get("strategy") or {},
                model=model_used,
                prompt_version=prompt_ver,
            )
            scored += 1
            if result.get("hard_filter_pass", True) and score >= min_score:
                high_score_ids.append(match_id)
        except Exception:  # noqa: BLE001
            errors += 1

    return {
        "scored": scored,
        "skipped_existing": skipped_existing,
        "errors": errors,
        "high_score_matches": len(high_score_ids),
        "high_score_match_ids": high_score_ids,
    }

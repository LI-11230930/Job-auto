"""Stage 2.3 + 2.4 + 2.6: Resume tailoring, factcheck retry loop, diff.md, QA, and greeting."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import UserConfig
from ..db import Database
from ..llm.base import LLMProvider, load_prompt_asset
from ..master import MasterProfile, QABank
from .factcheck import verify_tailored_resume
from .pdf_render import load_safe_display_contact, render_single_page_resume_pdf


def _safe_folder_name(job_id: int, company: str, title: str) -> str:
    slug = re.sub(r'[\\/:*?"<>|\s]+', "_", f"{job_id}_{company}_{title}").strip("_")
    return slug[:70]


def _build_fallback_raw_tailor(profile: MasterProfile, focus_tags: list[str], job_type: str) -> dict[str, Any]:
    """Safe deterministic fallback if LLM fails fact-check twice: pick Master bullets verbatim."""
    tag_set = {t.lower() for t in focus_tags}
    scored_bullets: list[tuple[int, str, str]] = []
    for exp in profile.experiences:
        for b in exp.bullets:
            overlap = sum(1 for t in b.tags if t.lower() in tag_set or any(k in t.lower() for k in tag_set))
            scored_bullets.append((overlap, b.id, b.text))
    scored_bullets.sort(key=lambda x: x[0], reverse=True)
    chosen = [{"id": bid, "rewritten": txt} for _, bid, txt in scored_bullets[:10]]
    summary = (
        f"2027届{profile.education.major}{profile.education.degree}，"
        "熟悉用友U8、金蝶云、金蝶EAS、畅捷通T+及Excel/Python财务数据处理。"
    )
    if job_type == "实习":
        summary += "求职财务/审计/ERP相关实习岗位。"
    else:
        summary += "求职财务培训生、财务管培及审计相关校招岗位。"
    return {"selected": chosen, "summary": summary}


def build_diff_markdown(
    *,
    job: dict[str, Any],
    match_row: dict[str, Any],
    profile: MasterProfile,
    tailored: dict[str, Any],
    factcheck_status: str,
    retry_count: int,
    violations_log: list[str],
    pdf_meta: dict[str, Any],
) -> str:
    orig_map = {b.id: b.text for exp in profile.experiences for b in exp.bullets}
    selected_ids = {str(x.get("id")) for x in tailored.get("selected") or []}
    lines = [
        f"# 投递包差异与事实核验报告 — {job.get('company')} · {job.get('title')}",
        "",
        f"- **岗位 ID**: `{job.get('id')}` | **批次**: `{job.get('job_type')}` | **匹配分**: `{match_row.get('score')}`",
        f"- **事实核验状态**: `{factcheck_status}`（重试次数: `{retry_count}`）",
        f"- **PDF 校验**: `{pdf_meta.get('page_count')} 页` / 可选中字符 `{pdf_meta.get('extracted_text_chars')}`",
        "",
        "## 个人定位摘要",
        f"> {tailored.get('summary', '')}",
        "",
        "## 选中要点对比（Master 原文 vs 定制输出）",
        "",
    ]
    for item in tailored.get("selected") or []:
        bid = str(item.get("id") or "")
        orig = orig_map.get(bid, "（未找到原文）")
        rewritten = str(item.get("rewritten") or "")
        changed = "已微调对齐" if orig != rewritten else "原句保留"
        lines.append(f"### `{bid}`（{changed}）")
        lines.append(f"- **Master 原文**: {orig}")
        lines.append(f"- **定制输出**: {rewritten}")
        lines.append("")

    omitted = [bid for bid in profile.all_bullet_ids() if bid not in selected_ids]
    if omitted:
        lines.append("## 未入选要点")
        for bid in omitted:
            lines.append(f"- `{bid}`: {orig_map[bid]}")
        lines.append("")

    if violations_log:
        lines.append("## 自动重写修正轨迹")
        lines.extend(violations_log)
        lines.append("")
    return "\n".join(lines)


def build_qa_and_greeting(
    *,
    job: dict[str, Any],
    profile: MasterProfile,
    qa_bank: QABank,
    cfg: UserConfig,
) -> tuple[dict[str, str], str]:
    """Assemble QA answers strictly from QABank + user config without fabricating English/skills."""
    qa_out: dict[str, str] = {}
    job_type = str(job.get("job_type") or "校招")
    for item in qa_bank.items:
        if item.category == "availability" and job_type != "实习":
            continue
        qa_out[item.question] = item.draft_answer

    eng = cfg.profile.english_status
    qa_out["英语水平与四六级情况"] = (
        f"暂未通过大学英语四级（CET-4 最高分 {eng.cet4_best_score or 418} 分），"
        f"{eng.gaokao_english}；可熟练阅读中文财报与财务ERP系统文档。"
    )

    company = str(job.get("company") or "")
    title = str(job.get("title") or "")
    if job_type == "实习":
        greeting = (
            f"您好！我是2027届{profile.education.major}本科生，熟悉用友U8、金蝶云、金蝶EAS、畅捷通T+及Excel/Python，"
            f"{cfg.profile.intern_availability}，非常希望能应聘{company}「{title}」实习岗位，随信附上定制简历。"
        )
    else:
        greeting = (
            f"您好！我是2027届{profile.education.major}本科生，具备多企业财务分析与ERP校内实训经历，"
            f"熟练使用用友U8、金蝶云/EAS及Excel/Python，非常关注{company}「{title}」校招机会，附上针对性简历请查收。"
        )
    return qa_out, greeting


def build_package_for_match(
    *,
    db: Database,
    cfg: UserConfig,
    llm: LLMProvider,
    prompts_root: Path,
    output_root: Path,
    job: dict[str, Any],
    match_row: dict[str, Any],
    master_version_id: int,
    profile: MasterProfile,
    qa_bank: QABank,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Run tailor -> factcheck retry loop -> 1-page PDF -> diff.md -> DB package record."""
    asset = load_prompt_asset(prompts_root, "resume_tailor")
    model_used = cfg.llm.default_model or asset.recommended_model
    strategy = json.loads(match_row.get("strategy_json") or "{}")
    job_type = str(job.get("job_type") or "校招")

    base_payload: dict[str, Any] = {
        "job": {
            "company": job.get("company"),
            "title": job.get("title"),
            "job_type": job_type,
            "jd_text": (job.get("jd_text") or "")[:3000],
        },
        "strategy": strategy,
        "master_profile": profile.model_dump(),
        "intern_availability": cfg.profile.intern_availability if job_type == "实习" else "",
    }

    tailored: dict[str, Any] = {}
    violations_log: list[str] = []
    factcheck_status = "blocked"
    retry_count = 0

    for attempt in range(max_retries + 1):
        payload = dict(base_payload)
        if attempt > 0 and violations_log:
            payload["retry_feedback"] = violations_log[-1]
        tailored = llm.generate_json(asset=asset, payload=payload, model_override=model_used)
        report = verify_tailored_resume(tailored, profile, job_type=job_type)
        if report.passed:
            factcheck_status = "pass"
            break
        retry_count = attempt + 1
        violations_log.append(f"第 {attempt + 1} 次校验未通过：\n{report.as_feedback()}")
    else:
        tailored = _build_fallback_raw_tailor(
            profile, strategy.get("focus_tags") or [], job_type=job_type
        )
        fallback_report = verify_tailored_resume(tailored, profile, job_type=job_type)
        factcheck_status = "fallback_raw" if fallback_report.passed else "blocked"

    pkg_dir = output_root / "packages" / _safe_folder_name(
        int(job["id"]), str(job["company"]), str(job["title"])
    )
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pkg_dir / "resume.pdf"
    diff_path = pkg_dir / "diff.md"

    vault_dir = Path(cfg.profile.vault_dir)
    if not vault_dir.is_absolute():
        vault_dir = output_root.parent / cfg.profile.vault_dir
    fallback_dir = Path(cfg.profile.resume_path) if cfg.profile.resume_path else None
    contact = load_safe_display_contact(vault_dir, fallback_resume_dir=fallback_dir)

    pdf_meta = render_single_page_resume_pdf(
        profile=profile,
        tailored=tailored,
        job=job,
        output_pdf_path=pdf_path,
        contact=contact,
        intern_availability=cfg.profile.intern_availability,
    )
    diff_md = build_diff_markdown(
        job=job,
        match_row=match_row,
        profile=profile,
        tailored=tailored,
        factcheck_status=factcheck_status,
        retry_count=retry_count,
        violations_log=violations_log,
        pdf_meta=pdf_meta,
    )
    diff_path.write_text(diff_md, encoding="utf-8")

    qa_out, greeting = build_qa_and_greeting(
        job=job, profile=profile, qa_bank=qa_bank, cfg=cfg
    )
    (pkg_dir / "qa.json").write_text(
        json.dumps({"qa": qa_out, "greeting": greeting}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    package_id = db.insert_package(
        job_id=int(job["id"]),
        match_id=int(match_row["id"]),
        master_version_id=master_version_id,
        resume_pdf_path=str(pdf_path),
        diff_md_path=str(diff_path),
        qa=qa_out,
        greeting=greeting,
        retry_count=retry_count,
        factcheck_status=factcheck_status,
        factcheck_log="\n\n".join(violations_log),
    )
    return {
        "package_id": package_id,
        "job_id": int(job["id"]),
        "company": job["company"],
        "title": job["title"],
        "score": match_row["score"],
        "factcheck_status": factcheck_status,
        "retry_count": retry_count,
        "pdf_path": str(pdf_path),
        "page_count": pdf_meta["page_count"],
    }

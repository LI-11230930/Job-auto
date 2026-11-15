"""Stage 4 delivery workflow helpers and autofill-extension exporter."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ..config import UserConfig, get_project_root
from ..db import Database
from ..master import MasterProfile, QABank, load_master_and_qa
from ..sources.base import DEFAULT_ALLOWED_SCHOOLS, is_restricted_university_portal


def _resolve_autofill_extension_dir() -> Path:
    env_path = os.getenv("JOB_AUTO_AUTOFILL_EXTENSION", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    bundled = get_project_root() / "extensions" / "job_auto_collector"
    return bundled


EXTENSION_PATH_DEFAULT = _resolve_autofill_extension_dir()

_DIRECT_CHAT_SOURCES = {"zhipin", "shixiseng", "zhaopin", "liepin", "51job", "nowcoder"}
_DIRECT_CHAT_DOMAINS = ("zhipin.com", "shixiseng.com", "zhaopin.com", "liepin.com", "51job.com")
_PORTAL_HINTS = (
    "beisen.com",
    "mokahr.com",
    "hotjob.cn",
    "italent.cn",
    "dayee.com",
    "zhiye.com",
    "zhaopin.cn",
    "careers.",
    "campus.",
    "join.",
    "hr.",
    "iguopin.com",
    "ncss.cn",
)


def classify_delivery_workflow(
    *,
    source: str | None = "",
    url: str | None = "",
    jd_text: str | None = "",
    apply_channel: str | None = "",
    apply_target: str | None = "",
) -> dict[str, Any]:
    """Classify post-approval workflow into HR direct chat, portal autofill, email, or restricted."""
    src = (source or "").strip().lower()
    raw_url = (url or apply_target or "").strip()
    lower_url = raw_url.lower()
    channel = (apply_channel or "").strip().lower()
    target = (apply_target or "").strip()

    if channel == "email" or target.lower().startswith("mailto:") or (
        "@" in target and not lower_url.startswith("http")
    ):
        return {
            "workflow": "email",
            "label": "邮件投递",
            "needs_autofill": False,
            "is_restricted": False,
            "badge_class": "wf-email",
            "next_step": "下载 {company}.pdf 并附带邮件自我介绍投递至目标邮箱（"
            + (target or "见简章")
            + "），无需官网填表。",
        }

    is_restricted, restricted_reason = is_restricted_university_portal(
        source=src,
        url=raw_url,
        jd_text=jd_text,
        apply_channel=channel,
        apply_target=target,
    )
    if is_restricted:
        return {
            "workflow": "restricted_campus",
            "label": f"外校认证受限（{restricted_reason}）",
            "needs_autofill": False,
            "is_restricted": True,
            "badge_class": "wf-stale",
            "next_step": f"该入口{restricted_reason}，非本校学生无法登录；请改用企业官方招聘邮箱/直招官网或归档移出。",
        }

    is_direct_board = src in _DIRECT_CHAT_SOURCES or any(
        dom in lower_url for dom in _DIRECT_CHAT_DOMAINS
    )
    has_portal_hint = any(hint in lower_url for hint in _PORTAL_HINTS)

    if channel == "company_portal" or (has_portal_hint and not is_direct_board):
        return {
            "workflow": "portal_autofill",
            "label": "官网网申（可用自动填写扩展）",
            "needs_autofill": True,
            "is_restricted": False,
            "badge_class": "wf-portal",
            "next_step": "打开企业官网网申页 -> 启动「智能简历自动填写助手」一键预填 -> 上传 {company}.pdf 后确认提交。",
        }

    if is_direct_board:
        return {
            "workflow": "direct_chat",
            "label": "HR直聊沟通（免官网填表）",
            "needs_autofill": False,
            "is_restricted": False,
            "badge_class": "wf-chat",
            "next_step": "直接与 HR 沟通发送打招呼话术并附上 {company}.pdf，直接确认笔试/面试时间，无需官网填表。",
        }

    return {
        "workflow": "portal_autofill",
        "label": "官网/平台网申（可用自动填写扩展）",
        "needs_autofill": True,
        "is_restricted": False,
        "badge_class": "wf-portal",
        "next_step": "打开目标网申入口，若需填写多栏表单可启用「智能简历自动填写助手」一键预填并上传 {company}.pdf。",
    }


def _split_period(period: str) -> tuple[str, str]:
    raw = (period or "").strip()
    if not raw:
        return "", ""
    parts = [p.strip() for p in re.split(r"\s*[-–—~至到]+\s*", raw) if p.strip()]
    if not parts:
        return "", ""

    def _norm_date(token: str) -> str:
        t = token.strip()
        if "至今" in t or t.lower() in {"present", "now"}:
            return "至今"
        return t.replace(".", "-").replace("/", "-")

    start = _norm_date(parts[0])
    end = _norm_date(parts[1]) if len(parts) > 1 else ""
    return start, end


def _load_runtime_secrets(vault_dir: Path | None) -> dict[str, str]:
    if vault_dir is None:
        return {}
    path = vault_dir / "personal_secrets.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v or "").strip() for k, v in raw.items() if isinstance(k, str)}


def _build_self_evaluation(profile: MasterProfile, qa_bank: QABank) -> str:
    for item in qa_bank.items:
        q = f"{item.category} {item.question}"
        if any(k in q for k in ("自我评价", "自我介绍", "个人优势", "核心竞争力")) and item.draft_answer.strip():
            return item.draft_answer.strip()
    certs = "、".join(profile.certifications[:4])
    courses = "、".join(profile.education.core_courses[:5])
    parts = [
        f"{profile.education.graduation_year}届{profile.education.major}{profile.education.degree}应届毕业生"
    ]
    if courses:
        parts.append(f"主修{courses}")
    if certs:
        parts.append(f"持有{certs}")
    if profile.skills:
        top_skills = "、".join(s.name for s in profile.skills[:5])
        parts.append(f"熟练使用{top_skills}")
    return "，".join(parts) + "。"


def _build_languages(cfg: UserConfig, profile: MasterProfile) -> list[dict[str, str]]:
    eng = cfg.profile.english_status
    cert = ""
    level = ""
    if eng.cet6_passed:
        cert = "英语六级 (CET-6)"
        level = "熟练"
    elif eng.cet4_passed:
        score = f"（{eng.cet4_best_score}分）" if eng.cet4_best_score else ""
        cert = f"英语四级备考/成绩{score}"
        level = "良好"
    elif eng.gaokao_english:
        cert = f"高考英语 {eng.gaokao_english}"
        level = "良好"
    elif any("英语" in c or "cet" in c.lower() for c in profile.certifications):
        cert = next(c for c in profile.certifications if "英语" in c or "cet" in c.lower())
        level = "良好"
    if not cert:
        return []
    return [{"name": "英语", "level": level, "certificate": cert}]


def _build_resume_schema_payload(
    *,
    cfg: UserConfig,
    profile: MasterProfile,
    qa_bank: QABank,
    secrets: dict[str, str],
    job_type_label: str,
    available_time: str,
) -> dict[str, Any]:
    edu_start, edu_end = _split_period(profile.education.period)
    cities = list(dict.fromkeys([*cfg.preferences.primary_cities, *cfg.preferences.secondary_cities]))
    demo_url = secrets.get("demo_url") or ""

    internships: list[dict[str, str]] = []
    projects: list[dict[str, str]] = []
    trainings: list[dict[str, str]] = []
    for exp in profile.experiences:
        s_date, e_date = _split_period(exp.period)
        desc = "\n".join(f"- {b.text}" for b in exp.bullets if b.text.strip())
        if exp.category == "internship":
            internships.append(
                {
                    "company": exp.organization,
                    "department": "",
                    "position": exp.role,
                    "startDate": s_date,
                    "endDate": e_date,
                    "description": desc,
                }
            )
        elif exp.category == "project":
            projects.append(
                {
                    "name": exp.organization,
                    "role": exp.role,
                    "startDate": s_date,
                    "endDate": e_date,
                    "description": desc,
                    "link": demo_url if ("ERP" in exp.organization or "数智" in exp.organization) else "",
                }
            )
        else:
            trainings.append(
                {
                    "institution": exp.organization,
                    "course": exp.role,
                    "certificate": "",
                    "startDate": s_date,
                    "endDate": e_date,
                    "description": desc,
                }
            )

    return {
        "basic": {
            "name": secrets.get("full_name") or secrets.get("name") or "",
            "gender": secrets.get("gender") or "",
            "birthday": secrets.get("birthday") or "",
            "age": secrets.get("age") or "",
            "phone": secrets.get("phone") or "",
            "email": secrets.get("email")
            or secrets.get("email_notify")
            or secrets.get("email_primary")
            or "",
            "idNumber": secrets.get("id_number") or "",
            "address": secrets.get("address") or secrets.get("city_intent") or "",
            "politics": secrets.get("political_status") or secrets.get("politics") or "",
            "nation": secrets.get("nation") or "",
            "nativePlace": secrets.get("hometown") or secrets.get("native_place") or "",
            "householdRegister": secrets.get("household_register")
            or secrets.get("hometown")
            or "",
            "maritalStatus": secrets.get("marital_status") or "未婚",
            "height": secrets.get("height") or "",
            "weight": secrets.get("weight") or "",
            "workYears": "应届生",
            "emergencyContactName": secrets.get("emergency_contact_name") or "",
            "emergencyContactRelation": secrets.get("emergency_contact_relation") or "",
            "emergencyContactPhone": secrets.get("emergency_contact_phone") or "",
        },
        "education": [
            {
                "school": profile.education.school,
                "department": profile.education.college,
                "major": profile.education.major,
                "degree": profile.education.degree,
                "educationType": "统招全日制",
                "schoolType": "",
                "startDate": edu_start,
                "endDate": edu_end,
                "description": (
                    f"主修课程：{'、'.join(profile.education.core_courses)}"
                    if profile.education.core_courses
                    else ""
                ),
            }
        ],
        "workExperience": [],
        "internship": internships,
        "project": projects,
        "training": trainings,
        "skills": [{"name": s.name, "level": s.level} for s in profile.skills],
        "certificates": [
            {"name": c, "issueDate": "", "issuer": "", "score": ""}
            for c in profile.certifications
        ],
        "languages": _build_languages(cfg, profile),
        "family": [],
        "selfEvaluation": _build_self_evaluation(profile, qa_bank),
        "jobIntent": {
            "position": " / ".join(cfg.profile.target_roles[:4]),
            "salary": secrets.get("expected_salary") or "",
            "city": secrets.get("city_intent") or "、".join(cities),
            "industry": "、".join(cfg.preferences.preferred_industries[:4]),
            "jobType": job_type_label,
            "availableTime": available_time,
        },
    }


def export_autofill_profile(
    *,
    cfg: UserConfig,
    db: Database | None = None,
    db_path: Path | None = None,
    output_path: Path | None = None,
    raw_output_path: Path | None = None,
    vault_dir: Path | None = None,
    profile_path: Path | None = None,
    qa_path: Path | None = None,
) -> dict[str, Any]:
    """Export MasterProfile + runtime secrets to resume-autofill-extension backup JSON."""
    root = get_project_root()
    resolved_vault = vault_dir or (root / cfg.profile.vault_dir)
    resolved_profile = profile_path or (resolved_vault / "master_profile.json")
    resolved_qa = qa_path or (resolved_vault / "qa_bank.json")
    target_backup = output_path or (root / "local" / "autofill_extension_backup.json")
    target_raw = raw_output_path or (root / "local" / "autofill_profile_raw.json")

    if resolved_profile.is_file():
        profile, qa_bank = load_master_and_qa(resolved_profile, resolved_qa)
    else:
        resolved_db = db or Database(db_path or (root / "data" / "job_agent.db"))
        master_row = resolved_db.get_latest_master_version()
        if master_row is None:
            raise RuntimeError(
                f"Master profile not found in DB or at {resolved_profile}; run import-master first."
            )
        profile = MasterProfile.model_validate_json(master_row["profile_json"])
        qa_bank = QABank.model_validate_json(master_row["qa_bank_json"])
    secrets = _load_runtime_secrets(resolved_vault)

    campus_data = _build_resume_schema_payload(
        cfg=cfg,
        profile=profile,
        qa_bank=qa_bank,
        secrets=secrets,
        job_type_label="全职/校招",
        available_time="2027届毕业前可提前实习 / 随时沟通",
    )
    intern_data = _build_resume_schema_payload(
        cfg=cfg,
        profile=profile,
        qa_bank=qa_bank,
        secrets=secrets,
        job_type_label="实习",
        available_time=cfg.profile.intern_availability or "每周到岗4-5天，可尽快到岗",
    )

    now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    backup_payload = {
        "app": "resume-autofill-extension",
        "version": "1.1.0",
        "exportedAt": datetime.now(tz=UTC).isoformat(),
        "data": {
            "activeProfileId": "job_agent_campus_2027",
            "resumeProfiles": [
                {
                    "id": "job_agent_campus_2027",
                    "name": "2027秋招/校招主档案",
                    "data": campus_data,
                    "createdAt": now_ms,
                },
                {
                    "id": "job_agent_intern_2027",
                    "name": "日常/暑期实习主档案",
                    "data": intern_data,
                    "createdAt": now_ms + 1,
                },
            ],
        },
    }

    target_backup.parent.mkdir(parents=True, exist_ok=True)
    target_backup.write_text(
        json.dumps(backup_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    target_raw.parent.mkdir(parents=True, exist_ok=True)
    target_raw.write_text(
        json.dumps(campus_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    basic = campus_data["basic"]
    filled_basic_count = sum(1 for v in basic.values() if str(v).strip())
    return {
        "backup_path": str(target_backup),
        "raw_profile_path": str(target_raw),
        "profiles_exported": 2,
        "basic_fields_filled": filled_basic_count,
        "internship_count": len(campus_data["internship"]),
        "project_count": len(campus_data["project"]),
        "skills_count": len(campus_data["skills"]),
        "certificates_count": len(campus_data["certificates"]),
        "extension_dir": str(EXTENSION_PATH_DEFAULT),
    }


def _parse_iso_dt(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _extract_intro_qa(qa: dict[str, Any] | None) -> str:
    if not isinstance(qa, dict):
        return ""
    for key, val in qa.items():
        if "自我介绍" in str(key) or "自我评价" in str(key):
            txt = str(val or "").strip()
            if txt:
                return txt
    return ""


def _extract_detail_supplement(jd_text: str | None) -> str:
    text = str(jd_text or "")
    marker = "【详情页补充】"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def _safe_company_pdf_stem(company: str, *, fallback: str = "resume") -> str:
    clean = re.sub(r'[\\/:*?"<>|]+', "_", (company or "").strip()).strip("_ ")
    return clean or fallback


def parse_ncss_detail_html(html_text: str) -> dict[str, Any]:
    """Extract full 职位详情 text, emails, and external URLs from NCSS detail HTML."""
    detail_text = ""
    m = re.search(
        r'<div[^>]*class="[^"]*mainContent[^"]*"[^>]*>(.*?)</div>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if m:
        raw_block = re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.IGNORECASE)
        raw_block = re.sub(r"</p\s*>", "\n", raw_block, flags=re.IGNORECASE)
        raw_block = re.sub(r"<[^>]+>", "", raw_block)
        detail_text = "\n".join(
            line.strip() for line in html.unescape(raw_block).splitlines() if line.strip()
        )

    site_match = re.search(
        r"公司网址.*?<span[^>]*>(.*?)</span>",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    company_site = ""
    if site_match:
        cand = re.sub(r"<[^>]+>", "", html.unescape(site_match.group(1))).strip()
        if cand and cand not in {"--", "-", "暂无"}:
            company_site = cand

    emails = sorted(
        {
            e
            for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", detail_text)
            if not e.lower().endswith("@ncss.cn")
        }
    )
    external_urls = [
        u
        for u in re.findall(r"https?://[^\s<>\"'）)]+", detail_text)
        if "ncss.cn" not in u.lower() and "chsi.com.cn" not in u.lower()
    ]
    return {
        "detail_text": detail_text,
        "company_site": company_site,
        "emails": emails,
        "external_urls": external_urls,
    }


def fetch_ncss_job_detail(
    url: str,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Politely fetch public NCSS job detail HTML and extract extra requirements/links."""
    clean_url = (url or "").strip()
    if not clean_url or "ncss.cn" not in clean_url.lower():
        return {"ok": False, "error": "not an ncss detail URL"}
    own_client = client is None
    sess = client or httpx.Client(
        trust_env=False,
        timeout=8.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    try:
        resp = sess.get(clean_url)
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        parsed = parse_ncss_detail_html(resp.text)
        return {"ok": True, **parsed}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if own_client:
            sess.close()


def summarize_delivery_tracker(
    db: Database,
    *,
    stale_days: int = 7,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Summarize approved applications split by track, delivery workflow, and stale reminders."""
    ref_now = now or datetime.now(tz=UTC)
    rows = db.list_applications(limit=500)

    enriched: list[dict[str, Any]] = []
    by_workflow = {
        "direct_chat": 0,
        "portal_autofill": 0,
        "email": 0,
        "restricted_campus": 0,
    }
    by_track = {"campus": 0, "intern": 0}
    by_status: dict[str, int] = {}
    stale_apps: list[dict[str, Any]] = []

    for row in rows:
        wf = classify_delivery_workflow(
            source=row.get("source"),
            url=row.get("url"),
            jd_text=row.get("jd_text"),
            apply_channel=row.get("apply_channel") or row.get("channel"),
            apply_target=row.get("apply_target"),
        )
        ref_ts = _parse_iso_dt(row.get("submitted_at") or row.get("updated_at"))
        days_elapsed = max(0, (ref_now - ref_ts).days) if ref_ts is not None else 0
        status = str(row.get("status") or "待提交")
        is_stale = status == "已投递" and days_elapsed >= stale_days
        company_stem = _safe_company_pdf_stem(str(row.get("company") or ""), fallback=f"job_{row.get('job_id')}")

        item = {
            **row,
            "workflow": wf["workflow"],
            "workflow_label": wf["label"],
            "needs_autofill": wf["needs_autofill"],
            "badge_class": wf["badge_class"],
            "next_step": wf["next_step"],
            "days_elapsed": days_elapsed,
            "is_stale": is_stale,
            "intro_answer": _extract_intro_qa(row.get("qa")),
            "detail_supplement": _extract_detail_supplement(row.get("jd_text")),
            "ready_pdf_name": f"{company_stem}.pdf",
        }
        enriched.append(item)
        by_workflow[wf["workflow"]] = by_workflow.get(wf["workflow"], 0) + 1
        if row.get("job_type") == "实习":
            by_track["intern"] += 1
        else:
            by_track["campus"] += 1
        by_status[status] = by_status.get(status, 0) + 1
        if is_stale:
            stale_apps.append(item)

    return {
        "total": len(enriched),
        "stale_days": stale_days,
        "by_workflow": by_workflow,
        "by_track": by_track,
        "by_status": by_status,
        "stale_count": len(stale_apps),
        "stale_applications": stale_apps,
        "applications": enriched,
    }


def prepare_delivery_bundles(
    db: Database,
    *,
    output_root: Path | None = None,
    enrich_ncss: bool = True,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Enrich approved jobs' details, stage upload-ready {company}.pdf files, and build checklist."""
    root = get_project_root()
    resolved_out = output_root or (root / "output")
    ready_root = resolved_out / "ready_to_submit"
    campus_dir = ready_root / "秋招"
    intern_dir = ready_root / "实习"
    campus_dir.mkdir(parents=True, exist_ok=True)
    intern_dir.mkdir(parents=True, exist_ok=True)

    rows = db.list_applications(limit=500)
    enriched_count = 0

    for row in rows:
        if row.get("status") == "已归档":
            continue
        if (
            enrich_ncss
            and str(row.get("source") or "").lower() == "ncss"
            and "【详情页补充】" not in str(row.get("jd_text") or "")
        ):
            detail = fetch_ncss_job_detail(str(row.get("url") or ""), client=client)
            if detail.get("ok"):
                extra_lines: list[str] = []
                if detail.get("detail_text"):
                    extra_lines.append(detail["detail_text"])
                if detail.get("company_site"):
                    extra_lines.append(f"公司网址：{detail['company_site']}")
                if detail.get("emails"):
                    extra_lines.append(f"提取邮箱：{', '.join(detail['emails'])}")
                if detail.get("external_urls"):
                    extra_lines.append(f"外链网申入口：{', '.join(detail['external_urls'])}")
                if extra_lines:
                    merged_jd = (
                        f"{str(row.get('jd_text') or '').rstrip()}\n【详情页补充】\n"
                        + "\n".join(extra_lines)
                    ).strip()
                    new_channel: str | None = None
                    new_target: str | None = None
                    if detail.get("emails") and row.get("apply_channel") != "company_portal":
                        new_channel = "email"
                        new_target = detail["emails"][0]
                    elif detail.get("external_urls"):
                        new_channel = "company_portal"
                        new_target = detail["external_urls"][0]
                    db.enrich_job_delivery_details(
                        job_id=int(row["job_id"]),
                        jd_text=merged_jd,
                        apply_channel=new_channel,
                        apply_target=new_target,
                    )
                    enriched_count += 1

    tracker = summarize_delivery_tracker(db)
    active_apps = [a for a in tracker["applications"] if a.get("status") != "已归档"]

    staged_files: list[str] = []
    seen_targets: set[Path] = set()
    prepared_items: list[dict[str, Any]] = []

    for app in active_apps:
        target_dir = intern_dir if app.get("job_type") == "实习" else campus_dir
        stem = _safe_company_pdf_stem(
            str(app.get("company") or ""), fallback=f"job_{app.get('job_id')}"
        )
        dest_pdf = target_dir / f"{stem}.pdf"
        if dest_pdf in seen_targets:
            dest_pdf = target_dir / f"{stem}_{app.get('job_id')}.pdf"
        seen_targets.add(dest_pdf)

        src_pdf = Path(str(app.get("resume_pdf_path") or ""))
        pdf_ready = False
        if src_pdf.is_file():
            shutil.copy2(src_pdf, dest_pdf)
            staged_files.append(str(dest_pdf))
            pdf_ready = True

        prepared_items.append(
            {
                **app,
                "staged_pdf_path": str(dest_pdf) if pdf_ready else "",
            }
        )

    lines: list[str] = [
        "# Stage 4 待投递执行清单（已按秋招 / 实习与直聊 / 官网扩展分流）",
        "",
        f"- 当前待推进岗位：**{len(prepared_items)}** 个（秋招/校招 {sum(1 for x in prepared_items if x.get('job_type') != '实习')} · 实习 {sum(1 for x in prepared_items if x.get('job_type') == '实习')}）",
        f"- 详情页补充抓取：**{enriched_count}** 个岗位",
        f"- 就绪简历目录：`{ready_root}`",
        "",
    ]
    for sec_title, subset in [
        ("一、秋招 / 校招投递清单", [x for x in prepared_items if x.get("job_type") != "实习"]),
        ("二、实习投递清单", [x for x in prepared_items if x.get("job_type") == "实习"]),
    ]:
        lines.append(f"## {sec_title}（{len(subset)} 项）")
        lines.append("")
        if not subset:
            lines.append("（暂无）")
            lines.append("")
            continue
        for idx, item in enumerate(subset, 1):
            company = item.get("company") or ""
            lines.extend(
                [
                    f"### {idx}. {company} · {item.get('title')}（{item.get('score') or '-'} 分｜状态：{item.get('status')}）",
                    f"- **投递方式**：{item.get('workflow_label')}",
                    f"- **目标链接**：{item.get('apply_target') or item.get('url') or '无'}",
                    f"- **上传附件**：`{item.get('staged_pdf_path') or item.get('resume_pdf_path') or '待生成'}`",
                    f"- **下一步操作**：{str(item.get('next_step') or '').replace('{company}', company)}",
                ]
            )
            if item.get("detail_supplement"):
                supp = " / ".join(line.strip() for line in item["detail_supplement"].splitlines() if line.strip())
                lines.append(f"- **详情页补充要点**：{supp}")
            if item.get("greeting"):
                lines.append(f"- **打招呼话术**：{item['greeting']}")
            if item.get("intro_answer"):
                lines.append(f"- **网申自我介绍（200-300字）**：{item['intro_answer']}")
            if item.get("notes"):
                lines.append(f"- **我的备注**：{item['notes']}")
            lines.append("")

    checklist_path = ready_root / "delivery_checklist.md"
    checklist_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "ready_root": str(ready_root),
        "checklist_path": str(checklist_path),
        "prepared_count": len(prepared_items),
        "enriched_count": enriched_count,
        "staged_pdfs": staged_files,
        "items": prepared_items,
    }


def open_application_in_edge(
    url: str,
    *,
    cdp_url: str = "http://127.0.0.1:9222",
) -> dict[str, Any]:
    """Open an application URL in a new tab inside the user's CDP Edge window."""
    target_url = (url or "").strip()
    if not target_url.startswith(("http://", "https://")):
        return {"ok": False, "error": f"无效的网页链接：{target_url}"}
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {"ok": False, "error": f"未安装 playwright：{exc}"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url, timeout=4000)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            page.bring_to_front()
            title = ""
            try:
                title = page.title()
            except PlaywrightError:
                title = ""
            return {"ok": True, "url": target_url, "title": title}
    except (PlaywrightError, OSError) as exc:
        return {
            "ok": False,
            "error": f"未检测到 9222 调试端口的 Edge/Chrome（可在工作台点击「启动带插件浏览器」或运行 job-agent up / start.bat）：{exc}",
        }


def cleanup_restricted_university_jobs(
    db: Database,
    *,
    allowed_schools: Sequence[str] = DEFAULT_ALLOWED_SCHOOLS,
) -> dict[str, int]:
    """Mark active jobs gated by external non-home university SSO portals as restricted_campus."""
    now_iso = datetime.now(UTC).isoformat()
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT id, source, url, jd_text, apply_channel, apply_target
            FROM jobs
            WHERE status = 'active'
            """
        ).fetchall()
        upgraded_job_ids = {
            int(r["job_id"])
            for r in conn.execute(
                """
                SELECT DISTINCT job_id
                FROM applications
                WHERE channel IN ('email', 'company_portal')
                """
            ).fetchall()
        }

        restricted_ids: list[tuple[str, int]] = []
        for row in rows:
            job_id = int(row["id"])
            if row["apply_channel"] in ("email", "company_portal") or job_id in upgraded_job_ids:
                continue
            restricted, _ = is_restricted_university_portal(
                source=row["source"],
                url=row["url"],
                jd_text=row["jd_text"],
                apply_channel=row["apply_channel"],
                apply_target=row["apply_target"],
                allowed_schools=allowed_schools,
            )
            if restricted:
                restricted_ids.append((now_iso, job_id))

        if restricted_ids:
            conn.executemany(
                "UPDATE jobs SET status = 'restricted_campus', updated_at = ? WHERE id = ?",
                restricted_ids,
            )

        remaining_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM jobs WHERE status = 'active'"
        ).fetchone()
        remaining = int(remaining_row["cnt"]) if remaining_row else 0

    return {
        "scanned": len(rows),
        "marked_restricted": len(restricted_ids),
        "remaining_active": remaining,
    }

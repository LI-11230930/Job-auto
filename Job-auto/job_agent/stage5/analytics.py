"""Stage 5.1 & 5.2: deadline/follow-up reminders and weekly funnel & tuning analytics."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from ..db import Database, normalize_job_type_filter
from ..sources.base import is_restricted_university_portal

_IN_PROGRESS_STATUSES = {"笔试中", "面试中", "测评", "面试"}
_SUBMITTED_STATUSES = {"已投递", "已提交", *_IN_PROGRESS_STATUSES, "Offer", "offer"}


def parse_deadline_date(raw: str | None) -> date | None:
    """Parse common Chinese/ISO deadline date strings into a local calendar date."""
    text = (raw or "").strip()
    if not text or any(tok in text for tok in ("长期", "招满", "不限", "持续")):
        return None
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _parse_iso_dt(raw: str | None) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _pct(num: int, den: int) -> float:
    return round((num / den) * 100.0, 1) if den > 0 else 0.0


def list_recent_runs(db: Database, *, limit: int = 12) -> list[dict[str, Any]]:
    """Return recent Stage 1-5 execution logs from the runs table."""
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT id, run_type, status, stats_json, error_log, started_at, finished_at
            FROM runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["stats"] = json.loads(item.get("stats_json") or "{}")
        except json.JSONDecodeError:
            item["stats"] = {}
        out.append(item)
    return out


def collect_reminders(
    db: Database,
    *,
    deadline_days: int = 7,
    stale_days: int = 7,
    today: date | None = None,
) -> dict[str, Any]:
    """Collect upcoming deadlines, stale follow-ups, active interviews, and urgent reviews."""
    ref_day = today or datetime.now().date()
    ref_now = datetime(ref_day.year, ref_day.month, ref_day.day, 23, 59, tzinfo=UTC)

    urgent_deadlines: list[dict[str, Any]] = []
    stale_followups: list[dict[str, Any]] = []
    in_progress_interviews: list[dict[str, Any]] = []
    restricted_queue_items: list[dict[str, Any]] = []

    apps = db.list_applications(limit=500)
    seen_deadline_job_ids: set[int] = set()

    for app in apps:
        jid = int(app["job_id"])
        status = str(app.get("status") or "待提交")
        restricted, reason = is_restricted_university_portal(
            source=app.get("source"),
            url=app.get("url"),
            jd_text=app.get("jd_text"),
            apply_channel=app.get("apply_channel") or app.get("channel"),
            apply_target=app.get("apply_target"),
        )
        if restricted and status != "已归档":
            restricted_queue_items.append(
                {
                    "application_id": app["id"],
                    "job_id": jid,
                    "company": app["company"],
                    "title": app["title"],
                    "job_type": app["job_type"],
                    "reason": reason,
                }
            )

        if status in _IN_PROGRESS_STATUSES:
            in_progress_interviews.append(
                {
                    "application_id": app["id"],
                    "company": app["company"],
                    "title": app["title"],
                    "job_type": app["job_type"],
                    "status": status,
                    "notes": app.get("notes") or "",
                    "updated_at": app.get("updated_at") or "",
                }
            )

        if status == "已投递":
            ref_dt = _parse_iso_dt(app.get("submitted_at") or app.get("updated_at"))
            elapsed = max(0, (ref_now - ref_dt).days) if ref_dt is not None else 0
            if elapsed >= stale_days:
                stale_followups.append(
                    {
                        "application_id": app["id"],
                        "company": app["company"],
                        "title": app["title"],
                        "job_type": app["job_type"],
                        "days_elapsed": elapsed,
                        "notes": app.get("notes") or "",
                    }
                )

    with db.connect() as conn:
        dl_rows = conn.execute(
            """
            SELECT j.id AS job_id, j.company, j.title, j.job_type, j.deadline, j.url, j.status AS job_status,
                   a.id AS application_id, a.status AS app_status,
                   m.score
            FROM jobs j
            LEFT JOIN applications a ON a.job_id = j.id
            LEFT JOIN matches m ON m.job_id = j.id
            WHERE j.deadline != '' AND j.status = 'active'
            ORDER BY j.id DESC
            """
        ).fetchall()

    for row in dl_rows:
        jid = int(row["job_id"])
        if jid in seen_deadline_job_ids:
            continue
        app_status = str(row["app_status"] or "")
        if app_status in {"已归档", "已投递", "已提交", "Offer", "offer"}:
            continue
        dl_date = parse_deadline_date(row["deadline"])
        if dl_date is None:
            continue
        score_val = int(row["score"]) if row["score"] is not None else 0
        is_relevant = row["application_id"] is not None or score_val >= 75
        if not is_relevant:
            continue
        days_left = (dl_date - ref_day).days
        if days_left < 0 and app_status != "待提交":
            continue
        if days_left <= deadline_days:
            seen_deadline_job_ids.add(jid)
            urgent_deadlines.append(
                {
                    "job_id": jid,
                    "company": row["company"],
                    "title": row["title"],
                    "job_type": row["job_type"],
                    "deadline": dl_date.isoformat(),
                    "days_left": days_left,
                    "score": row["score"],
                    "app_status": app_status or "待审核/未投",
                    "url": row["url"] or "",
                }
            )

    urgent_deadlines.sort(key=lambda item: (item["days_left"], -(item["score"] or 0)))

    pending_pkgs = db.list_packages_for_review(decision_filter="pending", min_score=85, limit=30)
    pending_high_score = [
        {
            "package_id": p["package_id"],
            "job_id": p["job_id"],
            "company": p["company"],
            "title": p["title"],
            "job_type": p["job_type"],
            "score": p["score"],
        }
        for p in pending_pkgs
    ]

    total_alerts = (
        len(urgent_deadlines)
        + len(stale_followups)
        + len(in_progress_interviews)
        + len(restricted_queue_items)
    )
    summary_parts = [
        f"截止日临近 {len(urgent_deadlines)} 项",
        f"投递超时待跟进 {len(stale_followups)} 项",
        f"笔试/面试推进中 {len(in_progress_interviews)} 项",
        f"高分待审 {len(pending_high_score)} 项",
    ]
    if restricted_queue_items:
        summary_parts.append(f"受限入口待替换 {len(restricted_queue_items)} 项")

    return {
        "as_of": ref_day.isoformat(),
        "deadline_days": deadline_days,
        "stale_days": stale_days,
        "total_alerts": total_alerts,
        "summary_text": " · ".join(summary_parts),
        "urgent_deadlines": urgent_deadlines,
        "stale_followups": stale_followups,
        "in_progress_interviews": in_progress_interviews,
        "pending_high_score": pending_high_score,
        "restricted_queue_items": restricted_queue_items,
    }


def _track_label(job_type: str | None) -> str:
    return "intern" if normalize_job_type_filter(job_type) == "实习" else "campus"


def _compute_tuning_suggestions(
    *,
    reject_reasons: list[tuple[str, int]],
    active_by_track: dict[str, int],
    total_restricted: int,
    pending_review_count: int,
    packages_total: int,
    submitted_total: int,
    stale_count: int,
    avg_match_score: float,
) -> list[str]:
    suggestions: list[str] = []
    if reject_reasons:
        top_reason, cnt = reject_reasons[0]
        suggestions.append(
            f"近期人工拒绝最常见原因为「{top_reason}」（{cnt} 次），"
            "可考虑将对应高频词汇加入 `config/user_config.yaml` 的 `excluded_keywords` 或下调相关偏好。"
        )
    if total_restricted > 0:
        suggestions.append(
            f"已累计拦截/隔离 {total_restricted} 条外校统一身份认证岗位；"
            "采集增量后建议保持自动运行 `cleanup-restricted`，聚焦公开直投通道。"
        )
    if active_by_track.get("intern", 0) > 0 and packages_total > 0:
        suggestions.append(
            "当前「秋招/校招」与「实习」均已隔离建包，建议按本周精力在周内优先跟进截止日明确的秋招，"
            "同步使用 `run-stage2 --job-type 实习` 补充可立刻到岗（12 月 24 日）的审计/ERP 实习。"
        )
    if pending_review_count >= 10:
        suggestions.append(
            f"工作台仍有 {pending_review_count} 份高分投递包待审，建议先清空高分待审池再发起下一批 Stage 2，避免堆积。"
        )
    elif packages_total > 0 and submitted_total == 0:
        suggestions.append(
            "已有定制完成且通过审核的投递包，建议按工作台「投递追踪队列」完成首批投递并点击「已投递」开启 7 天跟进计时。"
        )
    if stale_count > 0:
        suggestions.append(
            f"有 {stale_count} 项已投递记录超过 7 天未更新状态，建议补充跟进或标记为「笔试中/面试中/已归档」。"
        )
    if avg_match_score and avg_match_score < 70:
        suggestions.append(
            f"近期预筛后 LLM 平均匹配分偏低（{avg_match_score:.1f} 分），可收紧 Stage 2.1 `prefilter` 岗位信号词以提高命中率。"
        )
    if not suggestions:
        suggestions.append("当前转化链路健康，建议保持每日增量同步与每周固定复盘。")
    return suggestions


def build_weekly_report(
    db: Database,
    *,
    output_dir: Path | None = None,
    days: int = 7,
    stale_days: int = 7,
    today: date | None = None,
    write_files: bool = True,
) -> dict[str, Any]:
    """Generate Stage 5.2 weekly conversion funnel, rejection analytics, and tuning suggestions."""
    ref_day = today or datetime.now().date()
    cutoff_iso = (datetime(ref_day.year, ref_day.month, ref_day.day, tzinfo=UTC) - timedelta(days=days)).isoformat()

    with db.connect() as conn:
        job_rows = conn.execute(
            "SELECT id, source, job_type, cities_json, status, created_at FROM jobs"
        ).fetchall()
        match_rows = conn.execute(
            """
            SELECT m.id, m.score, m.rule_pass, m.created_at, j.job_type
            FROM matches m
            JOIN jobs j ON j.id = m.job_id
            """
        ).fetchall()
        pkg_rows = conn.execute(
            """
            SELECT p.id, p.factcheck_status, p.created_at, j.job_type, j.status AS job_status,
                   (SELECT d.decision FROM decisions d WHERE d.package_id = p.id ORDER BY d.id DESC LIMIT 1) AS decision
            FROM packages p
            JOIN jobs j ON j.id = p.job_id
            """
        ).fetchall()
        dec_rows = conn.execute(
            """
            SELECT d.decision, d.reason, d.decided_at, j.company, j.title, j.job_type, j.cities_json, j.source
            FROM decisions d
            JOIN jobs j ON j.id = d.job_id
            ORDER BY d.id DESC
            """
        ).fetchall()

    apps = db.list_applications(limit=500)
    reminders = collect_reminders(db, deadline_days=7, stale_days=stale_days, today=ref_day)
    recent_runs = list_recent_runs(db, limit=8)

    status_counts: Counter[str] = Counter()
    source_active: Counter[str] = Counter()
    active_by_track = {"campus": 0, "intern": 0}
    window_jobs = 0

    for r in job_rows:
        st = str(r["status"] or "active")
        status_counts[st] += 1
        if st == "active":
            source_active[str(r["source"] or "unknown")] += 1
            active_by_track[_track_label(r["job_type"])] += 1
        if str(r["created_at"] or "") >= cutoff_iso:
            window_jobs += 1

    match_scores = [int(r["score"]) for r in match_rows if r["score"] is not None]
    avg_score = round(sum(match_scores) / len(match_scores), 1) if match_scores else 0.0
    high_matches = sum(1 for s in match_scores if s >= 80)

    decisions_summary: Counter[str] = Counter()
    pkg_by_track = {"campus": 0, "intern": 0}
    for r in pkg_rows:
        dec = str(r["decision"] or "pending")
        if dec == "pending" and r["job_status"] == "restricted_campus":
            continue
        decisions_summary[dec] += 1
        pkg_by_track[_track_label(r["job_type"])] += 1

    reject_reasons: Counter[str] = Counter()
    reject_cities: Counter[str] = Counter()
    window_decisions = 0
    for r in dec_rows:
        if str(r["decided_at"] or "") >= cutoff_iso:
            window_decisions += 1
        if r["decision"] == "reject":
            reason = str(r["reason"] or "").strip() or "未填写理由"
            reject_reasons[reason] += 1
            try:
                cities = json.loads(r["cities_json"] or "[]")
            except json.JSONDecodeError:
                cities = []
            for c in cities[:2]:
                reject_cities[str(c)] += 1

    app_status_counts: Counter[str] = Counter()
    app_by_track = {
        "campus": {"total": 0, "submitted": 0, "in_progress": 0},
        "intern": {"total": 0, "submitted": 0, "in_progress": 0},
    }
    window_apps_updated = 0
    for app in apps:
        st = str(app.get("status") or "待提交")
        app_status_counts[st] += 1
        tr = _track_label(app.get("job_type"))
        app_by_track[tr]["total"] += 1
        if st in _SUBMITTED_STATUSES:
            app_by_track[tr]["submitted"] += 1
        if st in _IN_PROGRESS_STATUSES:
            app_by_track[tr]["in_progress"] += 1
        if str(app.get("updated_at") or "") >= cutoff_iso:
            window_apps_updated += 1

    reviewed_total = decisions_summary["approve"] + decisions_summary["reject"] + decisions_summary["later"]
    packages_total = sum(decisions_summary.values())
    approved_total = decisions_summary["approve"]
    submitted_total = sum(app_status_counts[s] for s in _SUBMITTED_STATUSES)
    in_progress_total = sum(app_status_counts[s] for s in _IN_PROGRESS_STATUSES)

    funnel = {
        "total_jobs": len(job_rows),
        "active_jobs": status_counts["active"],
        "restricted_campus_jobs": status_counts["restricted_campus"],
        "expired_jobs": status_counts["expired"],
        "filtered_out_jobs": status_counts["filtered_out"],
        "matches_total": len(match_rows),
        "high_matches_80plus": high_matches,
        "avg_match_score": avg_score,
        "packages_visible": packages_total,
        "packages_by_track": pkg_by_track,
        "decisions": {
            "approve": decisions_summary["approve"],
            "reject": decisions_summary["reject"],
            "later": decisions_summary["later"],
            "pending": decisions_summary["pending"],
        },
        "applications_total": len(apps),
        "applications_by_status": dict(app_status_counts),
        "applications_by_track": app_by_track,
        "rates": {
            "approval_rate_pct": _pct(approved_total, reviewed_total),
            "submission_rate_pct": _pct(submitted_total, len(apps)),
            "interview_advance_rate_pct": _pct(in_progress_total, submitted_total),
        },
    }

    top_rejects = reject_reasons.most_common(8)
    suggestions = _compute_tuning_suggestions(
        reject_reasons=top_rejects,
        active_by_track=active_by_track,
        total_restricted=status_counts["restricted_campus"],
        pending_review_count=decisions_summary["pending"],
        packages_total=packages_total,
        submitted_total=submitted_total,
        stale_count=len(reminders["stale_followups"]),
        avg_match_score=avg_score,
    )

    lines = [
        f"# Job-auto 每周求职复盘与调参报告（{ref_day.isoformat()} · 近 {days} 天）",
        "",
        "## 一、全链路转化漏斗",
        f"- 在库活跃岗位：**{status_counts['active']}** 条（近 {days} 天新增 {window_jobs} 条；已隔离外校认证受限 {status_counts['restricted_campus']} 条）",
        f"- 赛道活跃池：秋招/校招 `{active_by_track['campus']}` 条 · 实习 `{active_by_track['intern']}` 条",
        f"- AI 评分与定制：已评分 `{len(match_rows)}` 条（均分 `{avg_score}`，≥80 分 `{high_matches}` 条）→ 可审投递包 `{packages_total}` 份（秋招 `{pkg_by_track['campus']}` · 实习 `{pkg_by_track['intern']}`）",
        f"- 人工审核分布：通过 `{decisions_summary['approve']}` · 拒绝 `{decisions_summary['reject']}` · 暂缓 `{decisions_summary['later']}` · 待审 `{decisions_summary['pending']}`（审批通过率 `{funnel['rates']['approval_rate_pct']}%`）",
        f"- 投递队列进展：总入队 `{len(apps)}` 条（近 {days} 天更新 {window_apps_updated} 条）· 已投递及以上 `{submitted_total}` 条（投递转化率 `{funnel['rates']['submission_rate_pct']}%`）· 笔试/面试推进 `{in_progress_total}` 条",
        "",
        "## 二、重点提醒摘要",
        f"- {reminders['summary_text']}",
        "",
        "## 三、拒绝原因分布",
    ]
    if top_rejects:
        for reason, cnt in top_rejects:
            lines.append(f"- `{reason}`：{cnt} 次")
    else:
        lines.append("- （暂无拒绝决策记录）")

    lines.extend(["", "## 四、系统调参与行动建议"])
    for idx, tip in enumerate(suggestions, start=1):
        lines.append(f"{idx}. {tip}")

    markdown = "\n".join(lines) + "\n"

    payload: dict[str, Any] = {
        "as_of": ref_day.isoformat(),
        "window_days": days,
        "window_activity": {
            "new_jobs": window_jobs,
            "decisions": window_decisions,
            "applications_updated": window_apps_updated,
        },
        "funnel": funnel,
        "active_by_source": dict(source_active.most_common(12)),
        "active_by_track": active_by_track,
        "reject_reasons": [{"reason": r, "count": c} for r, c in top_rejects],
        "reject_cities": [{"city": c, "count": cnt} for c, cnt in reject_cities.most_common(6)],
        "reminders": reminders,
        "tuning_suggestions": suggestions,
        "recent_runs": recent_runs,
        "report_md_path": "",
        "report_json_path": "",
        "markdown": markdown,
    }

    if write_files and output_dir is not None:
        reports_dir = Path(output_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        md_path = reports_dir / f"weekly_report_{ref_day.isoformat()}.md"
        json_path = reports_dir / f"weekly_report_{ref_day.isoformat()}.json"
        md_path.write_text(markdown, encoding="utf-8")
        json_to_save = {k: v for k, v in payload.items() if k != "markdown"}
        json_path.write_text(json.dumps(json_to_save, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_md_path"] = str(md_path)
        payload["report_json_path"] = str(json_path)

    return payload

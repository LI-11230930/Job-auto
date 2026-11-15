"""Stage 3 daily digest builder and QQ SMTP notification helper."""

from __future__ import annotations

import html
import json
import os
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..config import UserConfig
from ..db import Database


def resolve_delivery_mode(cfg: UserConfig, channel: str) -> str:
    """Resolve delivery mode ('manual'|'assist'|'auto') from ChannelModes config."""
    mode = getattr(cfg.delivery.channel_modes, channel, "assist")
    return str(mode) if str(mode) in {"manual", "assist", "auto"} else "assist"


def _format_queue_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["（暂无记录）", ""]
    lines: list[str] = []
    for idx, row in enumerate(rows, start=1):
        cities = " / ".join(row.get("cities") or []) or "未标注"
        lines.extend(
            [
                f"### {idx}. {row.get('company')} · {row.get('title')}（{row.get('score') or '-'} 分）",
                f"- 批次：`{row.get('job_type')}` | 城市：`{cities}` | 渠道：`{row.get('channel')}` (`{row.get('mode')}`)",
                f"- 当前状态：**{row.get('status')}**",
                f"- 原链接：{row.get('url') or '无'}",
                f"- 定制简历：`{row.get('resume_pdf_path')}`",
                f"- 打招呼话术：{row.get('greeting') or ''}",
                "",
            ]
        )
    return lines


def export_approved_queue(
    db: Database,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """Export approved applications separated into 秋招/校招 vs 实习 checklists."""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    apps = db.list_applications(limit=200)
    campus_apps = [a for a in apps if a.get("job_type") != "实习"]
    intern_apps = [a for a in apps if a.get("job_type") == "实习"]

    md_path = output_dir / f"approved_queue_{today}.md"
    campus_md = output_dir / f"approved_queue_秋招_{today}.md"
    intern_md = output_dir / f"approved_queue_实习_{today}.md"
    json_path = output_dir / f"approved_queue_{today}.json"

    lines = [
        f"# 已确认待投递清单（{today}）",
        "",
        f"- 总计：**{len(apps)}** 条（秋招/校招：`{len(campus_apps)}` 条 | 实习：`{len(intern_apps)}` 条）",
        "",
        f"## 一、秋招 / 校招待投递（{len(campus_apps)} 条）",
        "",
        *_format_queue_rows(campus_apps),
        f"## 二、实习待投递（{len(intern_apps)} 条）",
        "",
        *_format_queue_rows(intern_apps),
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    campus_md.write_text(
        "\n".join([f"# 秋招/校招待投递清单（{today} · {len(campus_apps)} 条）", "", *_format_queue_rows(campus_apps)]),
        encoding="utf-8",
    )
    intern_md.write_text(
        "\n".join([f"# 实习待投递清单（{today} · {len(intern_apps)} 条）", "", *_format_queue_rows(intern_apps)]),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps({"campus": campus_apps, "intern": intern_apps}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "count": len(apps),
        "campus_count": len(campus_apps),
        "intern_count": len(intern_apps),
        "md_path": str(md_path),
        "campus_md_path": str(campus_md),
        "intern_md_path": str(intern_md),
        "json_path": str(json_path),
    }


def _format_digest_packages(pkgs: list[dict[str, Any]]) -> list[str]:
    if not pkgs:
        return ["（暂无）", ""]
    lines: list[str] = []
    for idx, pkg in enumerate(pkgs, start=1):
        cities = " / ".join(pkg.get("cities") or []) or "未标注"
        lines.extend(
            [
                f"### {idx}. [{pkg['score']} 分 | {pkg['decision']}] {pkg['company']} · {pkg['title']}",
                f"- 批次：`{pkg['job_type']}` | 城市：`{cities}` | 来源：`{pkg['source']}` | 核验：`{pkg['factcheck_status']}`",
                f"- 链接：{pkg.get('url') or '无'}",
                f"- 定制简历：`{pkg.get('resume_pdf_path')}`",
                "",
            ]
        )
    return lines


def _query_recent_active_jobs(db: Database, *, limit: int = 10) -> tuple[list[dict[str, Any]], int]:
    """Return latest active jobs plus count added in the last 24 hours."""
    cutoff_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    with db.connect() as conn:
        new_24h_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'active' AND created_at >= ?",
                (cutoff_24h,),
            ).fetchone()[0]
        )
        rows = conn.execute(
            """
            SELECT j.id, j.source, j.company, j.title, j.cities_json, j.job_type, j.url, j.deadline,
                   j.created_at,
                   (SELECT MAX(m.score) FROM matches m WHERE m.job_id = j.id) AS score
            FROM jobs j
            WHERE j.status = 'active'
            ORDER BY j.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    recent_jobs: list[dict[str, Any]] = []
    for row in rows:
        try:
            cities = json.loads(row["cities_json"] or "[]")
        except json.JSONDecodeError:
            cities = []
        recent_jobs.append(
            {
                "id": int(row["id"]),
                "source": str(row["source"] or ""),
                "company": str(row["company"] or ""),
                "title": str(row["title"] or ""),
                "cities": cities if isinstance(cities, list) else [],
                "job_type": str(row["job_type"] or "未知"),
                "url": str(row["url"] or ""),
                "deadline": str(row["deadline"] or ""),
                "created_at": str(row["created_at"] or ""),
                "score": int(row["score"]) if row["score"] is not None else None,
            }
        )
    return recent_jobs, new_24h_count


def build_daily_digest(
    db: Database,
    *,
    output_dir: Path,
    min_score: int = 80,
    top_n: int = 30,
) -> dict[str, Any]:
    """Build daily Stage 2/3 summary Markdown digest split by 秋招/校招 and 实习."""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    packages = db.list_packages_for_review(decision_filter="all", min_score=min_score, limit=top_n)
    apps = db.list_applications(limit=200)
    recent_active_jobs, new_24h_count = _query_recent_active_jobs(db, limit=10)

    with db.connect() as conn:
        total_jobs = int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        active_jobs = int(conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'active'").fetchone()[0])
        total_matches = int(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
        high_matches = int(
            conn.execute("SELECT COUNT(*) FROM matches WHERE score >= ?", (min_score,)).fetchone()[0]
        )

    pending_pkgs = [p for p in packages if p["decision"] == "pending"]
    approved_pkgs = [p for p in packages if p["decision"] == "approve"]
    campus_pkgs = [p for p in packages if p.get("job_type") != "实习"]
    intern_pkgs = [p for p in packages if p.get("job_type") == "实习"]

    lines = [
        f"# Job-auto 每日求职推荐与审核简报（{today}）",
        "",
        "## 一、全局漏斗概览",
        f"- 岗位总库：**{total_jobs}** 条（在库活跃：**{active_jobs}** 条 · 近 24 小时新入库：**{new_24h_count}** 条）",
        f"- AI 已评分：**{total_matches}** 条（其中 ≥{min_score} 分：**{high_matches}** 条）",
        f"- 已生成投递包：**{len(packages)}** 份（秋招/校招：`{len(campus_pkgs)}` 份 | 实习：`{len(intern_pkgs)}` 份）",
        f"- 审核状态：待人工复核 `{len(pending_pkgs)}` | 已确认通过 `{len(approved_pkgs)}` | 投递队列 `{len(apps)}`",
        "",
        f"## 二、秋招 / 校招高分定制投递包（{len(campus_pkgs)} 份）",
        "",
        *_format_digest_packages(campus_pkgs),
        f"## 三、实习高分定制投递包（{len(intern_pkgs)} 份）",
        "",
        *_format_digest_packages(intern_pkgs),
    ]

    digest_text = "\n".join(lines)
    digest_path = output_dir / f"daily_digest_{today}.md"
    digest_path.write_text(digest_text, encoding="utf-8")

    return {
        "date": today,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "new_24h_count": new_24h_count,
        "total_matches": total_matches,
        "high_matches": high_matches,
        "packages_count": len(packages),
        "campus_packages_count": len(campus_pkgs),
        "intern_packages_count": len(intern_pkgs),
        "pending_count": len(pending_pkgs),
        "approved_count": len(approved_pkgs),
        "applications_count": len(apps),
        "campus_packages": campus_pkgs,
        "intern_packages": intern_pkgs,
        "recent_active_jobs": recent_active_jobs,
        "digest_path": str(digest_path),
        "digest_markdown": digest_text,
    }


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _safe_http_url(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _pill_html(text: str, *, bg: str, fg: str, border: str = "transparent") -> str:
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        f'font-size:11px;font-weight:600;line-height:18px;background:{bg};color:{fg};'
        f'border:1px solid {border};white-space:nowrap;">{_esc(text)}</span>'
    )


def _decision_pill(decision: str) -> str:
    mapping = {
        "approve": ("已通过", "#ecfdf5", "#047857", "#a7f3d0"),
        "pending": ("待审核", "#eff6ff", "#1d4ed8", "#bfdbfe"),
        "later": ("暂缓", "#fffbeb", "#b45309", "#fde68a"),
        "reject": ("已拒绝", "#fef2f2", "#b91c1c", "#fecaca"),
    }
    label, bg, fg, border = mapping.get(decision, (decision or "待处理", "#f1f5f9", "#475569", "#cbd5e1"))
    return _pill_html(label, bg=bg, fg=fg, border=border)


def _render_package_cards(pkgs: list[dict[str, Any]], *, empty_label: str) -> str:
    if not pkgs:
        return (
            f'<div style="padding:14px 16px;border-radius:10px;background:#f8fafc;'
            f'border:1px dashed #cbd5e1;color:#64748b;font-size:13px;">{_esc(empty_label)}</div>'
        )
    cards: list[str] = []
    for pkg in pkgs:
        score = int(pkg.get("score") or 0)
        score_bg = "#059669" if score >= 88 else "#2563eb" if score >= 80 else "#475569"
        cities = " / ".join(pkg.get("cities") or []) or "未标注城市"
        fact_status = str(pkg.get("factcheck_status") or "pending")
        fact_bg, fact_fg = ("#ecfdf5", "#047857") if fact_status == "passed" else ("#fffbeb", "#b45309")
        safe_url = _safe_http_url(pkg.get("url"))
        link_btn = (
            f'<a href="{_esc(safe_url)}" target="_blank" rel="noopener noreferrer" '
            f'style="display:inline-block;padding:5px 12px;border-radius:6px;background:#1e40af;'
            f'color:#ffffff;text-decoration:none;font-size:12px;font-weight:600;">查看原帖 &rarr;</a>'
            if safe_url
            else '<span style="font-size:12px;color:#94a3b8;">暂无外链</span>'
        )
        cards.append(
            f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin-bottom:10px;border:1px solid #e2e8f0;border-radius:10px;background:#ffffff;">
              <tr>
                <td style="padding:14px 16px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td style="vertical-align:top;">
                        <div style="margin-bottom:6px;">
                          <span style="display:inline-block;padding:2px 9px;border-radius:6px;background:{score_bg};color:#ffffff;font-size:12px;font-weight:700;margin-right:6px;">{score} 分</span>
                          {_decision_pill(str(pkg.get("decision") or "pending"))}
                          <span style="margin-left:4px;">{_pill_html(f"核验: {fact_status}", bg=fact_bg, fg=fact_fg)}</span>
                        </div>
                        <div style="font-size:15px;font-weight:700;color:#0f172a;line-height:1.4;">
                          {_esc(pkg.get("company"))} &middot; {_esc(pkg.get("title"))}
                        </div>
                        <div style="margin-top:5px;font-size:12px;color:#475569;line-height:1.6;">
                          批次：<strong>{_esc(pkg.get("job_type") or "校招")}</strong>
                          &nbsp;&bull;&nbsp; 城市：{_esc(cities)}
                          &nbsp;&bull;&nbsp; 来源：{_esc(pkg.get("source") or "unknown")}
                        </div>
                      </td>
                      <td align="right" style="vertical-align:middle;padding-left:12px;white-space:nowrap;">
                        {link_btn}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            """.strip()
        )
    return "\n".join(cards)


def _render_reminders_block(reminders: dict[str, Any]) -> str:
    deadlines = reminders.get("urgent_deadlines") or []
    high_pending = reminders.get("pending_high_score") or []
    interviews = reminders.get("in_progress_interviews") or []
    stale = reminders.get("stale_followups") or []
    restricted = reminders.get("restricted_queue_items") or []

    rows_html: list[str] = []
    for item in deadlines[:5]:
        days_left = int(item.get("days_left") or 0)
        tag = "今日截止" if days_left == 0 else (f"逾期 {-days_left} 天" if days_left < 0 else f"剩 {days_left} 天")
        rows_html.append(
            f'<li style="margin-bottom:6px;font-size:13px;color:#1e293b;">'
            f'{_pill_html(tag, bg="#fef2f2", fg="#b91c1c", border="#fecaca")} '
            f'<strong>{_esc(item.get("company"))} &middot; {_esc(item.get("title"))}</strong>'
            f' <span style="color:#64748b;">(截止 {_esc(item.get("deadline"))})</span></li>'
        )
    for item in interviews[:4]:
        rows_html.append(
            f'<li style="margin-bottom:6px;font-size:13px;color:#1e293b;">'
            f'{_pill_html(str(item.get("status") or "推进中"), bg="#ecfdf5", fg="#047857", border="#a7f3d0")} '
            f'<strong>{_esc(item.get("company"))} &middot; {_esc(item.get("title"))}</strong></li>'
        )
    for item in stale[:4]:
        rows_html.append(
            f'<li style="margin-bottom:6px;font-size:13px;color:#1e293b;">'
            f'{_pill_html(f"已投 {item.get("days_elapsed", 0)} 天", bg="#fffbeb", fg="#b45309", border="#fde68a")} '
            f'<strong>{_esc(item.get("company"))} &middot; {_esc(item.get("title"))}</strong> 待跟进</li>'
        )
    for item in high_pending[:5]:
        rows_html.append(
            f'<li style="margin-bottom:6px;font-size:13px;color:#1e293b;">'
            f'{_pill_html(f"高分待审 {item.get("score", "-")}分", bg="#eff6ff", fg="#1d4ed8", border="#bfdbfe")} '
            f'<strong>{_esc(item.get("company"))} &middot; {_esc(item.get("title"))}</strong>'
            f' <span style="color:#64748b;">[{_esc(item.get("job_type"))}]</span></li>'
        )
    for item in restricted[:3]:
        rows_html.append(
            f'<li style="margin-bottom:6px;font-size:13px;color:#1e293b;">'
            f'{_pill_html("外校入口受限", bg="#fff7ed", fg="#c2410c", border="#fed7aa")} '
            f'<strong>{_esc(item.get("company"))} &middot; {_esc(item.get("title"))}</strong>'
            f' <span style="color:#64748b;">({_esc(item.get("reason") or "需改走公网官网")})</span></li>'
        )

    if not rows_html:
        return (
            '<div style="padding:12px 14px;border-radius:8px;background:#ecfdf5;border:1px solid #a7f3d0;'
            'color:#065f46;font-size:13px;">当前无紧急截止或超时跟进待办，节奏稳健。</div>'
        )
    return f'<ul style="margin:8px 0 0 0;padding-left:18px;line-height:1.6;">{"".join(rows_html)}</ul>'


def _render_recent_jobs_table(recent_jobs: list[dict[str, Any]]) -> str:
    if not recent_jobs:
        return '<div style="font-size:13px;color:#64748b;">暂无最近入库的活跃岗位。</div>'
    rows: list[str] = []
    for idx, job in enumerate(recent_jobs[:10]):
        bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
        cities = "/".join((job.get("cities") or [])[:2]) or "未标注"
        score = job.get("score")
        score_badge = (
            _pill_html(f"{score}分", bg="#dbeafe", fg="#1e40af")
            if score is not None
            else _pill_html("待筛选", bg="#f1f5f9", fg="#64748b")
        )
        safe_url = _safe_http_url(job.get("url"))
        title_cell = (
            f'<a href="{_esc(safe_url)}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#1d4ed8;text-decoration:none;font-weight:600;">{_esc(job.get("title"))}</a>'
            if safe_url
            else f'<span style="font-weight:600;color:#0f172a;">{_esc(job.get("title"))}</span>'
        )
        rows.append(
            f"""
            <tr style="background:{bg};">
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0f172a;font-weight:600;">{_esc(job.get("company"))}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;font-size:13px;">{title_cell}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#475569;white-space:nowrap;">{_esc(job.get("job_type"))}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#475569;">{_esc(cities)}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;font-size:12px;color:#64748b;">{_esc(job.get("source"))}</td>
              <td style="padding:9px 10px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap;">{score_badge}</td>
            </tr>
            """.strip()
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="border:1px solid #e2e8f0;border-radius:10px;border-collapse:collapse;overflow:hidden;">'
        '<thead><tr style="background:#f1f5f9;">'
        '<th align="left" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">公司</th>'
        '<th align="left" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">岗位</th>'
        '<th align="left" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">批次</th>'
        '<th align="left" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">城市</th>'
        '<th align="left" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">来源</th>'
        '<th align="right" style="padding:8px 10px;font-size:11px;color:#475569;border-bottom:1px solid #cbd5e1;">状态</th>'
        "</tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _render_source_bars(active_by_source: dict[str, int]) -> str:
    if not active_by_source:
        return '<div style="font-size:13px;color:#64748b;">暂无数据源分布。</div>'
    top_items = list(active_by_source.items())[:7]
    max_val = max((int(v) for _, v in top_items), default=1) or 1
    bars: list[str] = []
    for src, cnt in top_items:
        pct = max(4, min(100, round(int(cnt) * 100 / max_val)))
        bars.append(
            f"""
            <tr>
              <td style="padding:4px 8px 4px 0;font-size:12px;color:#334155;width:36%;word-break:break-all;">{_esc(src)}</td>
              <td style="padding:4px 8px;width:48%;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#e2e8f0;border-radius:999px;">
                  <tr>
                    <td width="{pct}%" bgcolor="#2563eb" height="8" style="border-radius:999px;font-size:1px;line-height:8px;">&nbsp;</td>
                    <td style="font-size:1px;line-height:8px;">&nbsp;</td>
                  </tr>
                </table>
              </td>
              <td align="right" style="padding:4px 0 4px 8px;font-size:12px;font-weight:700;color:#0f172a;width:16%;white-space:nowrap;">{int(cnt)}</td>
            </tr>
            """.strip()
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(bars)}</table>'


def render_daily_email_html(
    *,
    digest: dict[str, Any],
    reminders: dict[str, Any] | None = None,
    report: dict[str, Any] | None = None,
    workbench_url: str = "http://127.0.0.1:8788/review",
) -> str:
    """Render an email-client-safe responsive HTML daily求职简报."""
    reminders = reminders or {}
    report = report or {}
    funnel = report.get("funnel") or {}
    rates = funnel.get("rates") or {}
    active_by_source = report.get("active_by_source") or {}
    suggestions = report.get("tuning_suggestions") or []

    today = str(digest.get("date") or datetime.now().strftime("%Y-%m-%d"))
    active_jobs = int(funnel.get("active_jobs") or digest.get("active_jobs") or 0)
    total_jobs = int(funnel.get("total_jobs") or digest.get("total_jobs") or 0)
    new_24h = int(digest.get("new_24h_count") or 0)
    high_matches = int(digest.get("high_matches") or 0)
    pkg_count = int(digest.get("packages_count") or 0)
    campus_count = int(digest.get("campus_packages_count") or 0)
    intern_count = int(digest.get("intern_packages_count") or 0)
    pending_count = int(digest.get("pending_count") or 0)
    apps_count = int(digest.get("applications_count") or 0)
    total_alerts = int(reminders.get("total_alerts") or 0)
    summary_text = str(reminders.get("summary_text") or "暂无额外提醒")

    campus_pkgs = list(digest.get("campus_packages") or [])
    intern_pkgs = list(digest.get("intern_packages") or [])
    recent_jobs = list(digest.get("recent_active_jobs") or [])

    suggestions_html = (
        "".join(
            f'<li style="margin-bottom:5px;font-size:13px;color:#334155;">{_esc(tip)}</li>'
            for tip in suggestions[:5]
        )
        if suggestions
        else '<li style="font-size:13px;color:#64748b;">当前状态正常，建议持续补充目标企业与查看高分推荐。</li>'
    )

    alert_bg = "#fef2f2" if total_alerts > 0 else "#f8fafc"
    alert_fg = "#b91c1c" if total_alerts > 0 else "#334155"
    alert_border = "#fecaca" if total_alerts > 0 else "#e2e8f0"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Job-auto 每日求职简报 ({_esc(today)})</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f1f5f9;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0"
               style="max-width:680px;width:100%;background-color:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 18px rgba(15,23,42,0.06);">
          <!-- Hero Header -->
          <tr>
            <td bgcolor="#0f172a" style="background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#1d4ed8 100%);padding:26px 28px;color:#ffffff;">
              <div style="margin-bottom:10px;">
                <span style="display:inline-block;padding:3px 10px;border-radius:999px;background:rgba(255,255,255,0.16);color:#e0f2fe;font-size:11px;font-weight:700;letter-spacing:0.6px;">
                  JOB-AUTO &middot; 每日求职助手
                </span>
                <span style="display:inline-block;margin-left:8px;font-size:12px;color:#bfdbfe;">
                  {_esc(today)} &middot; 东八区 16:00 推送
                </span>
              </div>
              <div style="font-size:22px;font-weight:800;line-height:1.3;color:#ffffff;">
                每日求职汇总与待办提醒
              </div>
              <div style="margin-top:8px;font-size:13px;line-height:1.6;color:#dbeafe;">
                总库 {total_jobs} 岗 &nbsp;|&nbsp; 在库活跃 {active_jobs} 岗 &nbsp;|&nbsp; 24h 新入库 +{new_24h} 岗 &nbsp;|&nbsp; 高分包 {pkg_count} 份
              </div>
            </td>
          </tr>

          <!-- KPI 4-Grid -->
          <tr>
            <td style="padding:20px 24px 10px 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td width="25%" style="padding:0 5px 0 0;vertical-align:top;">
                    <div style="padding:12px;border-radius:10px;background:#eff6ff;border:1px solid #dbeafe;">
                      <div style="font-size:11px;color:#1d4ed8;font-weight:600;">在库活跃岗</div>
                      <div style="margin-top:4px;font-size:20px;font-weight:800;color:#0f172a;">{active_jobs}</div>
                      <div style="margin-top:2px;font-size:11px;color:#475569;">24h 新增 +{new_24h}</div>
                    </div>
                  </td>
                  <td width="25%" style="padding:0 5px;vertical-align:top;">
                    <div style="padding:12px;border-radius:10px;background:#ecfdf5;border:1px solid #d1fae5;">
                      <div style="font-size:11px;color:#047857;font-weight:600;">高分匹配(&ge;80)</div>
                      <div style="margin-top:4px;font-size:20px;font-weight:800;color:#0f172a;">{high_matches}</div>
                      <div style="margin-top:2px;font-size:11px;color:#475569;">秋招 {campus_count} &middot; 实习 {intern_count}</div>
                    </div>
                  </td>
                  <td width="25%" style="padding:0 5px;vertical-align:top;">
                    <div style="padding:12px;border-radius:10px;background:#fffbeb;border:1px solid #fde68a;">
                      <div style="font-size:11px;color:#b45309;font-weight:600;">人工复核 / 队列</div>
                      <div style="margin-top:4px;font-size:20px;font-weight:800;color:#0f172a;">{pending_count} / {apps_count}</div>
                      <div style="margin-top:2px;font-size:11px;color:#475569;">通过率 {rates.get("approval_rate_pct", 0)}%</div>
                    </div>
                  </td>
                  <td width="25%" style="padding:0 0 0 5px;vertical-align:top;">
                    <div style="padding:12px;border-radius:10px;background:{alert_bg};border:1px solid {alert_border};">
                      <div style="font-size:11px;color:{alert_fg};font-weight:600;">重点提醒事项</div>
                      <div style="margin-top:4px;font-size:20px;font-weight:800;color:{alert_fg};">{total_alerts}</div>
                      <div style="margin-top:2px;font-size:11px;color:#475569;">高分待审 {len(reminders.get("pending_high_score") or [])}</div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Reminders -->
          <tr>
            <td style="padding:12px 24px;">
              <div style="padding:16px;border-radius:10px;background:#f8fafc;border:1px solid #e2e8f0;">
                <div style="font-size:14px;font-weight:700;color:#0f172a;">一、重点提醒与待办</div>
                <div style="margin-top:4px;font-size:12px;color:#475569;">{_esc(summary_text)}</div>
                {_render_reminders_block(reminders)}
              </div>
            </td>
          </tr>

          <!-- Campus Track -->
          <tr>
            <td style="padding:10px 24px;">
              <div style="font-size:15px;font-weight:800;color:#0f172a;margin-bottom:10px;border-left:4px solid #2563eb;padding-left:10px;">
                二、秋招 / 校招高分推荐（{campus_count} 份）
              </div>
              {_render_package_cards(campus_pkgs, empty_label="当前暂无秋招/校招高分定制投递包（Stage 2 筛选暂未开启或待跑批）。")}
            </td>
          </tr>

          <!-- Intern Track -->
          <tr>
            <td style="padding:10px 24px;">
              <div style="font-size:15px;font-weight:800;color:#0f172a;margin-bottom:10px;border-left:4px solid #059669;padding-left:10px;">
                三、实习高分推荐（{intern_count} 份）
              </div>
              {_render_package_cards(intern_pkgs, empty_label="当前暂无实习高分定制投递包。")}
            </td>
          </tr>

          <!-- Recent Active Jobs -->
          <tr>
            <td style="padding:10px 24px;">
              <div style="font-size:15px;font-weight:800;color:#0f172a;margin-bottom:10px;border-left:4px solid #0284c7;padding-left:10px;">
                四、最新入库活跃岗位速览（Top 10）
              </div>
              {_render_recent_jobs_table(recent_jobs)}
            </td>
          </tr>

          <!-- Source Breakdown & Tuning Suggestions -->
          <tr>
            <td style="padding:12px 24px;">
              <div style="padding:16px;border-radius:10px;background:#f8fafc;border:1px solid #e2e8f0;">
                <div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:10px;">五、数据源分布与操作建议</div>
                {_render_source_bars(active_by_source)}
                <div style="margin-top:12px;padding-top:10px;border-top:1px solid #e2e8f0;">
                  <ul style="margin:0;padding-left:18px;line-height:1.65;">
                    {suggestions_html}
                  </ul>
                </div>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 24px 22px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
              <a href="{_esc(workbench_url)}" target="_blank" rel="noopener noreferrer"
                 style="display:inline-block;padding:10px 22px;border-radius:8px;background:#0f172a;color:#ffffff;text-decoration:none;font-size:13px;font-weight:700;">
                打开本地审核与投递追踪台
              </a>
              <div style="margin-top:10px;font-size:11px;color:#64748b;line-height:1.5;">
                本地服务地址：<code>{_esc(workbench_url)}</code> &middot; 由 Job-auto 自动生成与推送
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_qq_email_digest(
    cfg: UserConfig,
    *,
    subject: str,
    body_text: str,
    html_body: str | None = None,
) -> dict[str, Any]:
    """Send daily digest via any configured SMTP provider (QQ/163/Gmail/Outlook/Custom)."""
    notif = cfg.notifications
    if notif.provider == "none":
        return {"status": "disabled", "email_to": notif.email_to}

    host = (os.getenv(notif.smtp_host_env, "") or notif.smtp_host or "").strip()
    user = os.getenv(notif.smtp_user_env, "").strip()
    password = os.getenv(notif.smtp_pass_env, "").strip()
    port_raw = (
        os.getenv(notif.smtp_port_env, "").strip()
        or (str(notif.smtp_port) if notif.smtp_port else "")
        or "465"
    )
    email_to = (notif.email_to or os.getenv("EMAIL_TO", "") or user).strip()

    missing = [
        name
        for name, val in (
            (notif.smtp_host_env, host),
            (notif.smtp_user_env, user),
            (notif.smtp_pass_env, password),
        )
        if not val
    ]
    if missing:
        return {
            "status": "skipped_missing_smtp_env",
            "missing_env": missing,
            "email_to": email_to,
        }

    port = int(port_raw)
    security = (notif.smtp_security or "auto").strip().lower()
    if security == "auto":
        security = "ssl" if port == 465 else "starttls"

    recipients = [r.strip() for r in email_to.replace(";", ",").split(",") if r.strip()]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(recipients) if recipients else email_to
    msg.set_content(body_text)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    elif security == "starttls":
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)

    return {
        "status": "sent",
        "email_to": msg["To"],
        "host": host,
        "port": port,
        "security": security,
        "has_html": bool(html_body),
    }


send_email_digest = send_qq_email_digest

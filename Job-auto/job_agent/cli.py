"""CLI entrypoint for Job-auto Stage 1 operations."""

from __future__ import annotations

import argparse
import json
from itertools import islice
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .config import get_project_root, load_user_config
from .db import Database
from .launcher import bootstrap_workspace, collect_system_status, run_unified_app

_SUPPORTED_COLLECT_SITES = ("zhipin", "51job", "iguopin", "zhaopin")
_HEAVY_DEPS_LOADED = False


def _ensure_heavy_cli_deps() -> None:
    """Lazy-load heavy pipeline, scraper, and PDF modules only when CLI subcommands invoke them."""
    global _HEAVY_DEPS_LOADED
    if _HEAVY_DEPS_LOADED:
        return
    from .inbox_server import create_inbox_app
    from .llm.openai_compat import build_llm_provider
    from .master import MasterProfile, QABank, load_master_and_qa
    from .progress import update_progress_artifacts
    from .sources.assisted_browser import SITE_URLS, collect_via_assisted_browser
    from .sources.campus_site_readonly import CampusSiteReadonlyAdapter
    from .sources.edge_takeover import collect_from_open_edge_cdp, collect_portal_sweep_cdp
    from .sources.html_import import import_snapshot_path
    from .sources.manual_ingest import build_manual_job, split_summary_post
    from .sources.ncss import NcssPublicAdapter
    from .sources.shixiseng import ShixisengPublicAdapter
    from .sources.zhaopin_public import ZhaopinPublicAdapter
    from .stage2.matcher import run_match_batch
    from .stage2.prefilter import select_prefilter_candidates
    from .stage2.tailor import build_package_for_match
    from .stage3.digest import (
        build_daily_digest,
        render_daily_email_html,
        resolve_delivery_mode,
        send_qq_email_digest,
    )
    from .stage3.review_server import create_review_app
    from .stage4 import (
        cleanup_restricted_university_jobs,
        export_autofill_profile,
        prepare_delivery_bundles,
        summarize_delivery_tracker,
    )
    from .stage5 import build_weekly_report, collect_reminders, run_daily_cycle

    globals().update(locals())
    _HEAVY_DEPS_LOADED = True


def _default_db_path() -> Path:
    return get_project_root() / "data" / "job_agent.db"


def _maybe_refresh_progress(db_path: Path) -> None:
    if db_path.resolve() == _default_db_path().resolve():
        update_progress_artifacts(db_path=db_path)


def cmd_init_db(db_path: Path) -> None:
    db = Database(db_path)
    db.init_schema()
    print(json.dumps({"status": "ok", "db_path": str(db_path)}, ensure_ascii=False))


def cmd_sync_campus(db_path: Path, *, limit: int | None, exclude_social: bool) -> None:
    cfg = load_user_config()
    raw_path = (cfg.data_sources.campus_site_jobs_path or "").strip()
    if not raw_path or not Path(raw_path).is_file():
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "campus_site_jobs_path 未配置或文件不存在，已自动跳过。",
                },
                ensure_ascii=False,
            )
        )
        return
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run("ingest_campus_readonly")
    try:
        adapter = CampusSiteReadonlyAdapter(
            cfg.data_sources.campus_site_jobs_path,
            exclude_social=exclude_social,
        )
        stream = adapter.fetch_jobs()
        batch = list(islice(stream, limit)) if limit else list(stream)
        stats = db.upsert_jobs(batch)
        stats["total_in_db"] = db.count_jobs()
        db.finish_run(run_id, status="completed", stats=stats)
        print(json.dumps({"status": "ok", "run_id": run_id, **stats}, ensure_ascii=False))
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_import_master(db_path: Path, *, profile_path: Path, qa_path: Path | None) -> None:
    db = Database(db_path)
    db.init_schema()
    profile, qa_bank = load_master_and_qa(profile_path, qa_path)
    row_id = db.upsert_master_version(
        version_tag=profile.version_tag,
        profile_json=profile.model_dump_json(),
        qa_bank_json=qa_bank.model_dump_json(),
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "master_version_id": row_id,
                "version_tag": profile.version_tag,
                "bullet_count": len(profile.all_bullet_ids()),
                "qa_count": len(qa_bank.items),
            },
            ensure_ascii=False,
        )
    )


def cmd_add_jd(
    db_path: Path,
    *,
    company: str,
    title: str,
    cities: str,
    job_type: str,
    url: str,
    jd_file: Path,
) -> None:
    db = Database(db_path)
    db.init_schema()
    jd_text = jd_file.read_text(encoding="utf-8")
    job = build_manual_job(
        company=company,
        title=title,
        jd_text=jd_text,
        cities=cities,
        job_type=job_type,
        url=url,
    )
    stats = db.upsert_jobs([job])
    print(json.dumps({"status": "ok", **stats, "total_in_db": db.count_jobs()}, ensure_ascii=False))


def cmd_split_jd(db_path: Path, *, text_file: Path) -> None:
    cfg = load_user_config()
    db = Database(db_path)
    db.init_schema()
    raw_text = text_file.read_text(encoding="utf-8")
    provider = build_llm_provider(cfg)
    jobs = split_summary_post(
        raw_text=raw_text,
        llm=provider,
        prompts_root=get_project_root() / "prompts",
        model_override=cfg.llm.lite_model,
    )
    stats = db.upsert_jobs(jobs)
    print(
        json.dumps(
            {"status": "ok", "extracted": len(jobs), **stats, "total_in_db": db.count_jobs()},
            ensure_ascii=False,
        )
    )


def cmd_stats(db_path: Path) -> None:
    db = Database(db_path)
    if not db_path.exists():
        print(json.dumps({"status": "uninitialized", "db_path": str(db_path)}, ensure_ascii=False))
        return
    with db.connect() as conn:
        by_type = {
            row["job_type"]: row["cnt"]
            for row in conn.execute("SELECT job_type, COUNT(*) AS cnt FROM jobs GROUP BY job_type")
        }
        total = db.count_jobs()
    latest_master = db.get_latest_master_version()
    print(
        json.dumps(
            {
                "total_jobs": total,
                "by_job_type": by_type,
                "latest_master_version": latest_master["version_tag"] if latest_master else None,
            },
            ensure_ascii=False,
        )
    )


def cmd_sync_public(
    db_path: Path,
    *,
    sources: list[str],
    max_pages: int,
    exclude_social: bool,
) -> None:
    db = Database(db_path)
    db.init_schema()
    adapter_map = {
        "ncss": lambda: NcssPublicAdapter(max_pages=max_pages),
        "zhaopin": lambda: ZhaopinPublicAdapter(
            max_pages=max_pages, exclude_social=exclude_social
        ),
        "shixiseng": lambda: ShixisengPublicAdapter(max_pages=max_pages),
    }
    summary: dict[str, Any] = {}
    for src_name in sources:
        factory = adapter_map.get(src_name)
        if not factory:
            raise ValueError(f"Unknown public source '{src_name}'")
        run_id = db.start_run(f"ingest_public_{src_name}")
        adapter = factory()
        try:
            batch = list(adapter.fetch_jobs())
            stats = db.upsert_jobs(batch)
            stats["fetched"] = len(batch)
            stats["errors"] = len(getattr(adapter, "errors", []))
            db.finish_run(
                run_id,
                status="completed",
                stats=stats,
                error_log="\n".join(getattr(adapter, "errors", [])[:10]),
            )
            summary[src_name] = stats
        except Exception as exc:
            db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
            raise
    _maybe_refresh_progress(db_path)
    print(
        json.dumps(
            {"status": "ok", "sources": summary, "total_in_db": db.count_jobs()},
            ensure_ascii=False,
        )
    )


def cmd_import_html(
    db_path: Path,
    *,
    target_path: Path,
    site: str,
    exclude_social: bool,
) -> None:
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run(f"import_html_{site}")
    try:
        jobs = import_snapshot_path(target_path, site=site, exclude_social=exclude_social)
        stats = db.upsert_jobs(jobs)
        stats["extracted"] = len(jobs)
        db.finish_run(run_id, status="completed", stats=stats)
        _maybe_refresh_progress(db_path)
        print(
            json.dumps(
                {"status": "ok", **stats, "total_in_db": db.count_jobs()},
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_collect_browser(
    db_path: Path,
    *,
    site: str,
    exclude_social: bool,
    auto_pages: int = 3,
    page_delay_seconds: float = 4.5,
) -> None:
    root = get_project_root()
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run(f"collect_browser_{site}")
    try:
        jobs = collect_via_assisted_browser(
            site=site,
            user_data_dir=root / "data" / "browser_profiles" / site,
            exclude_social=exclude_social,
            save_snapshot_dir=root / "data" / "inbox" / site,
            auto_pages=auto_pages,
            page_delay_seconds=page_delay_seconds,
        )
        stats = db.upsert_jobs(jobs)
        stats["extracted"] = len(jobs)
        db.finish_run(run_id, status="completed", stats=stats)
        _maybe_refresh_progress(db_path)
        print(
            json.dumps(
                {"status": "ok", **stats, "total_in_db": db.count_jobs()},
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_prefilter(
    db_path: Path,
    *,
    limit: int,
    allow_nationwide: bool,
    apply_mark: bool,
    job_type: str = "all",
) -> None:
    cfg = load_user_config()
    db = Database(db_path)
    selected, stats = select_prefilter_candidates(
        db,
        cfg,
        limit=limit,
        allow_nationwide=allow_nationwide,
        mark_filtered_out=apply_mark,
        job_type_filter=job_type,
    )
    sample = [
        {
            "id": j["id"],
            "source": j["source"],
            "company": j["company"],
            "title": j["title"],
            "cities": json.loads(j.get("cities_json") or "[]"),
            "job_type": j["job_type"],
            "city_tier": o.city_tier,
            "rule_score_hint": o.rule_score_hint,
        }
        for j, o in selected[:15]
    ]
    print(json.dumps({"status": "ok", "stats": stats, "top_sample": sample}, ensure_ascii=False))


def cmd_run_stage2(
    db_path: Path,
    *,
    match_limit: int,
    package_limit: int,
    allow_nationwide: bool,
    job_type: str = "all",
) -> None:
    root = get_project_root()
    cfg = load_user_config()
    db = Database(db_path)
    master_row = db.get_latest_master_version()
    if master_row is None:
        raise RuntimeError("Master profile not found in DB; run import-master first.")
    profile = MasterProfile.model_validate_json(master_row["profile_json"])
    qa_bank = QABank.model_validate_json(master_row["qa_bank_json"])
    master_id = int(master_row["id"])

    run_id = db.start_run("stage2_match_and_package")
    try:
        candidates_with_meta, pf_stats = select_prefilter_candidates(
            db,
            cfg,
            limit=match_limit,
            allow_nationwide=allow_nationwide,
            mark_filtered_out=False,
            job_type_filter=job_type,
        )
        from .company_check import filter_and_verify_prefilter_candidates

        candidate_jobs, cc_stats = filter_and_verify_prefilter_candidates(
            db, cfg, candidates_with_meta, root=root
        )

        provider = build_llm_provider(cfg)
        prompts_root = root / "prompts"
        match_stats = run_match_batch(
            db=db,
            cfg=cfg,
            llm=provider,
            prompts_root=prompts_root,
            candidates=candidate_jobs,
            master_version_id=master_id,
            profile=profile,
        )

        pending_pairs = db.get_matches_needing_packages(
            master_version_id=master_id,
            min_score=cfg.scoring.min_score_for_package,
            limit=package_limit,
        )
        built_packages: list[dict[str, Any]] = []
        for job_dict, match_row in pending_pairs:
            pkg = build_package_for_match(
                db=db,
                cfg=cfg,
                llm=provider,
                prompts_root=prompts_root,
                output_root=root / "output",
                job=job_dict,
                match_row=match_row,
                master_version_id=master_id,
                profile=profile,
                qa_bank=qa_bank,
            )
            built_packages.append(pkg)

        combined = {
            "prefilter": pf_stats,
            "company_check": cc_stats,
            "match": {k: v for k, v in match_stats.items() if k != "high_score_match_ids"},
            "packages_built": len(built_packages),
        }
        db.finish_run(run_id, status="completed", stats=combined)
        _maybe_refresh_progress(db_path)
        print(
            json.dumps(
                {"status": "ok", "run_id": run_id, **combined, "packages": built_packages},
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_listen_inbox(db_path: Path, *, host: str, port: int) -> None:
    import uvicorn

    app = create_inbox_app(db_path=db_path)
    print(
        f"[Job-auto 本地采集接收服务] 已启动：http://{host}:{port}\n"
        "请在普通 Edge 浏览器中点击「Job-auto 本地职位采集助手」扩展一键采集当前页，按 Ctrl+C 停止。"
    )
    uvicorn.run(app, host=host, port=port, log_level="warning")


def cmd_takeover_edge(
    db_path: Path,
    *,
    cdp_url: str,
    site: str,
    max_scrolls: int,
    max_pages: int,
    exclude_social: bool,
) -> None:
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run(f"edge_takeover:{site}")
    try:
        res = collect_from_open_edge_cdp(
            cdp_url=cdp_url,
            site_filter=site,
            save_snapshot_dir=get_project_root() / "data" / "inbox",
            max_scrolls=max_scrolls,
            max_pages=max_pages,
            exclude_social=exclude_social,
        )
        jobs = res["jobs"]
        counts = db.upsert_jobs(jobs)
        stats = {"tabs": res["tabs"], "extracted": len(jobs), **counts}
        db.finish_run(run_id, status="completed", stats=stats)
        _maybe_refresh_progress(db_path)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "run_id": run_id,
                    **stats,
                    "total_in_db": db.count_jobs(),
                },
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_takeover_sweep(
    db_path: Path,
    *,
    cdp_url: str,
    site: str,
    max_scrolls: int,
    exclude_social: bool,
) -> None:
    db = Database(db_path)
    db.init_schema()
    run_id = db.start_run(f"edge_takeover_sweep:{site}")
    inserted_total = 0
    updated_total = 0
    skipped_total = 0

    def _on_batch(batch_jobs: list[dict[str, Any]]) -> None:
        nonlocal inserted_total, updated_total, skipped_total
        c = db.upsert_jobs(batch_jobs)
        inserted_total += c["inserted"]
        updated_total += c["updated"]
        skipped_total += c["skipped"]

    try:
        res = collect_portal_sweep_cdp(
            cdp_url=cdp_url,
            site_filter=site,
            save_snapshot_dir=get_project_root() / "data" / "inbox",
            max_scrolls=max_scrolls,
            exclude_social=exclude_social,
            on_batch=_on_batch,
        )
        stats = {
            "queries": res["queries"],
            "extracted": len(res["jobs"]),
            "inserted": inserted_total,
            "updated": updated_total,
            "skipped": skipped_total,
        }
        db.finish_run(run_id, status="completed", stats=stats)
        _maybe_refresh_progress(db_path)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "run_id": run_id,
                    **stats,
                    "total_in_db": db.count_jobs(),
                },
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats={}, error_log=str(exc))
        raise


def cmd_review(db_path: Path, *, host: str, port: int) -> None:
    import uvicorn

    root = get_project_root()
    app = create_review_app(db_path=db_path, output_root=root / "output")
    print(f"[Job-auto Stage 3 人工复核工作台] 已启动：http://{host}:{port}/review")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def cmd_digest(db_path: Path, *, min_score: int, top_n: int, send_email: bool) -> None:
    root = get_project_root()
    cfg = load_user_config()
    db = Database(db_path)
    db.init_schema()
    res = build_daily_digest(
        db,
        output_dir=root / "output" / "digest",
        min_score=min_score,
        top_n=top_n,
        cfg=cfg,
    )
    reminders = collect_reminders(db)
    report = build_weekly_report(db, write_files=False)
    html_body = render_daily_email_html(digest=res, reminders=reminders, report=report)
    html_path = root / "output" / "digest" / f"daily_email_{res['date']}.html"
    html_path.write_text(html_body, encoding="utf-8")

    digest_md = res.pop("digest_markdown", "")
    res.pop("campus_packages", None)
    res.pop("intern_packages", None)
    res.pop("recent_active_jobs", None)
    res["email_html_path"] = str(html_path)
    email_res: dict[str, Any] | None = None
    if send_email:
        email_res = send_qq_email_digest(
            cfg,
            subject=f"Job-auto 每日求职简报 ({res['date']}) · 高分 {res['high_matches']} 岗",
            body_text=digest_md,
            html_body=html_body,
        )
    print(json.dumps({"status": "ok", **res, "email": email_res}, ensure_ascii=False))


def cmd_decide(db_path: Path, *, package_id: int, decision: str, reason: str) -> None:
    cfg = load_user_config()
    db = Database(db_path)
    detail = db.get_package_detail(package_id)
    if detail is None:
        raise RuntimeError(f"Package not found: {package_id}")
    channel = str(detail.get("apply_channel") or "unknown")
    mode = resolve_delivery_mode(cfg, channel)
    res = db.record_decision(package_id=package_id, decision=decision, reason=reason, default_mode=mode)
    print(json.dumps({"status": "ok", **res}, ensure_ascii=False))


def cmd_export_autofill(
    db_path: Path,
    *,
    output: Path | None,
    raw_output: Path | None,
) -> None:
    cfg = load_user_config()
    res = export_autofill_profile(cfg=cfg, db_path=db_path, output_path=output, raw_output_path=raw_output)
    print(json.dumps({"status": "ok", **res}, ensure_ascii=False))


def cmd_prepare_delivery(db_path: Path, *, enrich: bool) -> None:
    root = get_project_root()
    db = Database(db_path)
    db.init_schema()
    res = prepare_delivery_bundles(db, output_root=root / "output", enrich_ncss=enrich)
    print(
        json.dumps(
            {
                "status": "ok",
                "ready_root": res["ready_root"],
                "checklist_path": res["checklist_path"],
                "prepared_count": res["prepared_count"],
                "enriched_count": res["enriched_count"],
                "staged_pdfs": res["staged_pdfs"],
            },
            ensure_ascii=False,
        )
    )


def cmd_cleanup_restricted(db_path: Path) -> None:
    db = Database(db_path)
    db.init_schema()
    res = cleanup_restricted_university_jobs(db)
    _maybe_refresh_progress(db_path)
    print(json.dumps({"status": "ok", **res}, ensure_ascii=False))


def cmd_reminders(
    db_path: Path,
    *,
    deadline_days: int,
    stale_days: int,
    send_email: bool,
) -> None:
    cfg = load_user_config()
    db = Database(db_path)
    db.init_schema()
    res = collect_reminders(db, deadline_days=deadline_days, stale_days=stale_days)
    email_res: dict[str, Any] | None = None
    if send_email:
        lines = [
            f"# Job-auto 截止日与跟进提醒（{res['as_of']}）",
            "",
            res["summary_text"],
            "",
            f"- 截止日临近：{len(res['urgent_deadlines'])} 项",
            f"- 投递超时（≥{stale_days} 天）：{len(res['stale_followups'])} 项",
            f"- 笔面试推进中：{len(res['in_progress_interviews'])} 项",
            f"- 高分待审（≥85 分）：{len(res['pending_high_score'])} 项",
        ]
        email_res = send_qq_email_digest(
            cfg,
            subject=f"[Job-auto] 截止日与跟进提醒（{res['total_alerts']} 项）",
            body_text="\n".join(lines),
        )
    print(json.dumps({"status": "ok", **res, "email": email_res}, ensure_ascii=False))


def cmd_weekly_report(
    db_path: Path,
    *,
    days: int,
    stale_days: int,
    send_email: bool,
) -> None:
    root = get_project_root()
    cfg = load_user_config()
    db = Database(db_path)
    db.init_schema()
    report = build_weekly_report(
        db,
        output_dir=root / "output" / "reports",
        days=days,
        stale_days=stale_days,
        write_files=True,
    )
    email_res: dict[str, Any] | None = None
    if send_email:
        email_res = send_qq_email_digest(
            cfg,
            subject=f"[Job-auto] 每周求职复盘与调参报告（{report['as_of']}）",
            body_text=report["markdown"],
        )
    summary = {k: v for k, v in report.items() if k != "markdown"}
    _maybe_refresh_progress(db_path)
    print(json.dumps({"status": "ok", **summary, "email": email_res}, ensure_ascii=False))


def cmd_daily_cycle(
    db_path: Path,
    *,
    sync_sources: bool,
    sync_edge: bool,
    cdp_url: str,
    edge_sweep: bool,
    run_prefilter: bool,
    run_llm: bool,
    match_limit: int,
    package_limit: int,
    job_type: str,
    allow_nationwide: bool,
    send_email: bool,
    send_reminder: bool = False,
) -> None:
    root = get_project_root()
    cfg = load_user_config()
    db = Database(db_path)
    res = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=root / "output",
        prompts_root=root / "prompts",
        sync_sources=sync_sources,
        sync_edge=sync_edge,
        cdp_url=cdp_url,
        edge_sweep=edge_sweep,
        run_prefilter=run_prefilter,
        run_llm=run_llm,
        match_limit=match_limit,
        package_limit=package_limit,
        job_type=job_type,
        allow_nationwide=allow_nationwide,
        send_email=send_email,
        send_reminder=send_reminder,
    )
    print(json.dumps(res, ensure_ascii=False))


def cmd_track(db_path: Path, *, stale_days: int) -> None:
    db = Database(db_path)
    db.init_schema()
    summary = summarize_delivery_tracker(db, stale_days=stale_days)
    compact_apps = [
        {
            "id": a["id"],
            "company": a["company"],
            "title": a["title"],
            "job_type": a["job_type"],
            "workflow": a["workflow"],
            "workflow_label": a["workflow_label"],
            "needs_autofill": a["needs_autofill"],
            "status": a["status"],
            "days_elapsed": a["days_elapsed"],
            "is_stale": a["is_stale"],
            "channel": a["channel"],
            "url": a["url"],
        }
        for a in summary["applications"]
    ]
    print(
        json.dumps(
            {
                "status": "ok",
                "total": summary["total"],
                "stale_days": summary["stale_days"],
                "stale_count": summary["stale_count"],
                "by_workflow": summary["by_workflow"],
                "by_track": summary["by_track"],
                "by_status": summary["by_status"],
                "applications": compact_apps,
            },
            ensure_ascii=False,
        )
    )


def cmd_update_progress(
    db_path: Path,
    *,
    milestone_title: str | None,
    milestone_detail: str | None,
    test_count: int | None,
    current_stage: str | None,
    position: str | None,
    next_goal: str | None,
    sync_stages: bool = False,
) -> None:
    res = update_progress_artifacts(
        db_path=db_path,
        milestone_title=milestone_title,
        milestone_detail=milestone_detail,
        test_count=test_count,
        current_stage=current_stage,
        position=position,
        next_goal=next_goal,
        sync_stages=sync_stages,
    )
    print(json.dumps({"status": "ok", **res}, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-agent")
    parser.add_argument("--db", type=Path, default=_default_db_path())
    sub = parser.add_subparsers(dest="command", required=False)

    up_p = sub.add_parser("up", aliases=["start"])
    up_p.add_argument("--host", default="127.0.0.1")
    up_p.add_argument("--port", type=int, default=8788)
    up_p.add_argument("--cdp-port", type=int, default=9222)
    up_p.add_argument("--no-browser", action="store_true")
    up_p.add_argument("--no-cdp", action="store_true")
    up_p.add_argument("--app", action="store_true")

    sub.add_parser("setup")
    doc_p = sub.add_parser("doctor")
    doc_p.add_argument("--cdp-url", default="http://127.0.0.1:9222")

    sub.add_parser("init-db")

    sync_p = sub.add_parser("sync-campus")
    sync_p.add_argument("--limit", type=int, default=None)
    sync_p.add_argument("--exclude-social", action="store_true")

    pub_p = sub.add_parser("sync-public")
    pub_p.add_argument("--sources", default="ncss,zhaopin,shixiseng")
    pub_p.add_argument("--max-pages", type=int, default=1)
    pub_p.add_argument("--include-social", action="store_true")

    html_p = sub.add_parser("import-html")
    html_p.add_argument("--path", type=Path, required=True)
    html_p.add_argument("--site", default="auto")
    html_p.add_argument("--include-social", action="store_true")

    col_p = sub.add_parser("collect-browser")
    col_p.add_argument("--site", required=True, choices=list(_SUPPORTED_COLLECT_SITES))
    col_p.add_argument("--include-social", action="store_true")
    col_p.add_argument("--auto-pages", type=int, default=3)
    col_p.add_argument("--delay", type=float, default=4.5)

    pf_p = sub.add_parser("prefilter")
    pf_p.add_argument("--limit", type=int, default=50)
    pf_p.add_argument("--allow-nationwide", action="store_true")
    pf_p.add_argument("--apply", action="store_true")
    pf_p.add_argument("--job-type", default="all", choices=["all", "秋招", "校招", "实习"])

    s2_p = sub.add_parser("run-stage2")
    s2_p.add_argument("--match-limit", type=int, default=15)
    s2_p.add_argument("--package-limit", type=int, default=5)
    s2_p.add_argument("--allow-nationwide", action="store_true")
    s2_p.add_argument("--job-type", default="all", choices=["all", "秋招", "校招", "实习"])

    im_p = sub.add_parser("import-master")
    im_p.add_argument("--profile", type=Path, required=True)
    im_p.add_argument("--qa", type=Path, default=None)

    add_p = sub.add_parser("add-jd")
    add_p.add_argument("--company", required=True)
    add_p.add_argument("--title", required=True)
    add_p.add_argument("--cities", default="")
    add_p.add_argument("--job-type", default="校招")
    add_p.add_argument("--url", default="")
    add_p.add_argument("--jd-file", type=Path, required=True)

    split_p = sub.add_parser("split-jd")
    split_p.add_argument("--file", type=Path, required=True)

    sub.add_parser("stats")

    prog_p = sub.add_parser("update-progress")
    prog_p.add_argument("--milestone-title", default=None)
    prog_p.add_argument("--milestone-detail", default=None)
    prog_p.add_argument("--test-count", type=int, default=None)
    prog_p.add_argument("--stage", default=None)
    prog_p.add_argument("--position", default=None)
    prog_p.add_argument("--next-goal", default=None)
    prog_p.add_argument("--sync-stages", action="store_true")

    inb_p = sub.add_parser("listen-inbox")
    inb_p.add_argument("--host", default="127.0.0.1")
    inb_p.add_argument("--port", type=int, default=8765)

    tk_p = sub.add_parser("takeover-edge")
    tk_p.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    tk_p.add_argument(
        "--site",
        default="auto",
        choices=["auto", "zhipin", "zhaopin", "51job", "iguopin", "shixiseng"],
    )
    tk_p.add_argument("--max-scrolls", type=int, default=30)
    tk_p.add_argument("--max-pages", type=int, default=1)
    tk_p.add_argument("--include-social", action="store_true")

    sw_p = sub.add_parser("takeover-sweep")
    sw_p.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    sw_p.add_argument("--site", default="all", choices=["all", "zhaopin", "shixiseng"])
    sw_p.add_argument("--max-scrolls", type=int, default=8)
    sw_p.add_argument("--include-social", action="store_true")

    rev_p = sub.add_parser("review")
    rev_p.add_argument("--host", default="127.0.0.1")
    rev_p.add_argument("--port", type=int, default=8788)

    dig_p = sub.add_parser("digest")
    dig_p.add_argument("--min-score", type=int, default=80)
    dig_p.add_argument("--top-n", type=int, default=30)
    dig_p.add_argument("--send-email", action="store_true")

    dec_p = sub.add_parser("decide")
    dec_p.add_argument("--package-id", type=int, required=True)
    dec_p.add_argument("--decision", required=True, choices=["approve", "reject", "later"])
    dec_p.add_argument("--reason", default="")

    auto_p = sub.add_parser("export-autofill")
    auto_p.add_argument("--output", type=Path, default=None)
    auto_p.add_argument("--raw-output", type=Path, default=None)

    trk_p = sub.add_parser("track")
    trk_p.add_argument("--stale-days", type=int, default=7)

    prep_p = sub.add_parser("prepare-delivery")
    prep_p.add_argument("--no-enrich", action="store_true")

    sub.add_parser("cleanup-restricted")

    rem_p = sub.add_parser("reminders")
    rem_p.add_argument("--days", type=int, default=7)
    rem_p.add_argument("--stale-days", type=int, default=7)
    rem_p.add_argument("--send-email", action="store_true")

    rep_p = sub.add_parser("weekly-report")
    rep_p.add_argument("--days", type=int, default=7)
    rep_p.add_argument("--stale-days", type=int, default=7)
    rep_p.add_argument("--send-email", action="store_true")

    day_p = sub.add_parser("daily-cycle")
    day_p.add_argument("--skip-sync", action="store_true")
    day_p.add_argument("--skip-edge", action="store_true")
    day_p.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    day_p.add_argument("--edge-sweep", action="store_true")
    day_p.add_argument("--skip-prefilter", action="store_true")
    day_p.add_argument("--skip-llm", action="store_true")
    day_p.add_argument("--match-limit", type=int, default=15)
    day_p.add_argument("--package-limit", type=int, default=6)
    day_p.add_argument("--job-type", default="all", choices=["all", "秋招", "校招", "实习"])
    day_p.add_argument("--allow-nationwide", action="store_true")
    day_p.add_argument("--send-email", action="store_true")
    day_p.add_argument("--notify", action="store_true")

    args = parser.parse_args(argv)
    load_dotenv(get_project_root() / ".env", override=False)
    if args.command in (None, "up", "start"):
        return run_unified_app(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8788),
            db_path=args.db,
            cdp_port=getattr(args, "cdp_port", 9222),
            open_browser=not getattr(args, "no_browser", False),
            launch_cdp=not getattr(args, "no_cdp", False),
            app_mode=getattr(args, "app", False),
        )
    if args.command == "setup":
        print(json.dumps(bootstrap_workspace(db_path=args.db), ensure_ascii=False, indent=2))
        return 0
    if args.command == "doctor":
        print(
            json.dumps(
                collect_system_status(db_path=args.db, cdp_url=args.cdp_url),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    _ensure_heavy_cli_deps()
    if args.command == "init-db":
        cmd_init_db(args.db)
    elif args.command == "sync-campus":
        cmd_sync_campus(args.db, limit=args.limit, exclude_social=args.exclude_social)
    elif args.command == "sync-public":
        src_list = [s.strip() for s in args.sources.split(",") if s.strip()]
        cmd_sync_public(
            args.db,
            sources=src_list,
            max_pages=args.max_pages,
            exclude_social=not args.include_social,
        )
    elif args.command == "import-html":
        cmd_import_html(
            args.db,
            target_path=args.path,
            site=args.site,
            exclude_social=not args.include_social,
        )
    elif args.command == "collect-browser":
        cmd_collect_browser(
            args.db,
            site=args.site,
            exclude_social=not args.include_social,
            auto_pages=args.auto_pages,
            page_delay_seconds=args.delay,
        )
    elif args.command == "prefilter":
        cmd_prefilter(
            args.db,
            limit=args.limit,
            allow_nationwide=args.allow_nationwide,
            apply_mark=args.apply,
            job_type=args.job_type,
        )
    elif args.command == "run-stage2":
        cmd_run_stage2(
            args.db,
            match_limit=args.match_limit,
            package_limit=args.package_limit,
            allow_nationwide=args.allow_nationwide,
            job_type=args.job_type,
        )
    elif args.command == "import-master":
        cmd_import_master(args.db, profile_path=args.profile, qa_path=args.qa)
    elif args.command == "add-jd":
        cmd_add_jd(
            args.db,
            company=args.company,
            title=args.title,
            cities=args.cities,
            job_type=args.job_type,
            url=args.url,
            jd_file=args.jd_file,
        )
    elif args.command == "split-jd":
        cmd_split_jd(args.db, text_file=args.file)
    elif args.command == "stats":
        cmd_stats(args.db)
    elif args.command == "update-progress":
        cmd_update_progress(
            args.db,
            milestone_title=args.milestone_title,
            milestone_detail=args.milestone_detail,
            test_count=args.test_count,
            current_stage=args.stage,
            position=args.position,
            next_goal=args.next_goal,
            sync_stages=args.sync_stages,
        )
    elif args.command == "listen-inbox":
        cmd_listen_inbox(args.db, host=args.host, port=args.port)
    elif args.command == "takeover-edge":
        cmd_takeover_edge(
            args.db,
            cdp_url=args.cdp_url,
            site=args.site,
            max_scrolls=args.max_scrolls,
            max_pages=args.max_pages,
            exclude_social=not args.include_social,
        )
    elif args.command == "takeover-sweep":
        cmd_takeover_sweep(
            args.db,
            cdp_url=args.cdp_url,
            site=args.site,
            max_scrolls=args.max_scrolls,
            exclude_social=not args.include_social,
        )
    elif args.command == "review":
        cmd_review(args.db, host=args.host, port=args.port)
    elif args.command == "digest":
        cmd_digest(args.db, min_score=args.min_score, top_n=args.top_n, send_email=args.send_email)
    elif args.command == "decide":
        cmd_decide(args.db, package_id=args.package_id, decision=args.decision, reason=args.reason)
    elif args.command == "export-autofill":
        cmd_export_autofill(args.db, output=args.output, raw_output=args.raw_output)
    elif args.command == "track":
        cmd_track(args.db, stale_days=args.stale_days)
    elif args.command == "prepare-delivery":
        cmd_prepare_delivery(args.db, enrich=not args.no_enrich)
    elif args.command == "cleanup-restricted":
        cmd_cleanup_restricted(args.db)
    elif args.command == "reminders":
        cmd_reminders(
            args.db,
            deadline_days=args.days,
            stale_days=args.stale_days,
            send_email=args.send_email,
        )
    elif args.command == "weekly-report":
        cmd_weekly_report(
            args.db,
            days=args.days,
            stale_days=args.stale_days,
            send_email=args.send_email,
        )
    elif args.command == "daily-cycle":
        cmd_daily_cycle(
            args.db,
            sync_sources=not args.skip_sync,
            sync_edge=not args.skip_edge,
            cdp_url=args.cdp_url,
            edge_sweep=args.edge_sweep,
            run_prefilter=not args.skip_prefilter,
            run_llm=not args.skip_llm,
            match_limit=args.match_limit,
            package_limit=args.package_limit,
            job_type=args.job_type,
            allow_nationwide=args.allow_nationwide,
            send_email=args.send_email,
            send_reminder=args.notify,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Stage 3.2 & 5: single-command daily pipeline orchestration with runs audit logging."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from ..config import UserConfig, get_project_root, load_user_config
from ..db import Database
from ..llm.base import LLMProvider
from ..llm.openai_compat import build_llm_provider
from ..master import MasterProfile, QABank
from ..notifications import dispatch_notification
from ..progress import update_progress_artifacts
from ..sources.campus_site_readonly import CampusSiteReadonlyAdapter
from ..sources.edge_takeover import collect_from_open_edge_cdp, collect_portal_sweep_cdp
from ..sources.ncss import NcssPublicAdapter
from ..sources.shixiseng import ShixisengPublicAdapter
from ..sources.zhaopin_public import ZhaopinPublicAdapter
from ..stage2.matcher import run_match_batch
from ..stage2.prefilter import select_prefilter_candidates
from ..stage2.tailor import build_package_for_match
from ..stage3.digest import build_daily_digest, render_daily_email_html, send_qq_email_digest
from ..stage4.delivery import cleanup_restricted_university_jobs, prepare_delivery_bundles
from .analytics import build_weekly_report, collect_reminders


def _run_public_sync_step(db: Database, cfg: UserConfig) -> dict[str, Any]:
    """Run polite public/readonly ingestion adapters cleanly, isolating per-source failures."""
    step: dict[str, Any] = {"sources": {}, "errors": []}
    exclude_social = True

    campus_path_str = (cfg.data_sources.campus_site_jobs_path or "").strip()
    campus_path = Path(campus_path_str) if campus_path_str else None
    if campus_path and campus_path.is_file():
        try:
            campus_jobs = list(
                CampusSiteReadonlyAdapter(campus_path, exclude_social=exclude_social).fetch_jobs()
            )
            step["sources"]["campus_site"] = db.upsert_jobs(campus_jobs)
        except (OSError, ValueError) as exc:  # pragma: no cover - defensive runtime guard
            step["errors"].append(f"campus_site: {exc}")

    if cfg.data_sources.enable_extra_public_sources:
        adapters = (
            NcssPublicAdapter(max_pages=1),
            ZhaopinPublicAdapter(max_pages=1, exclude_social=exclude_social),
            ShixisengPublicAdapter(max_pages=1),
        )
        for adapter in adapters:
            try:
                rows = list(adapter.fetch_jobs())
                step["sources"][adapter.source_name] = {
                    "fetched": len(rows),
                    **db.upsert_jobs(rows),
                }
            except (httpx.HTTPError, OSError, ValueError) as exc:  # pragma: no cover - defensive network guard
                step["errors"].append(f"{adapter.source_name}: {exc}")

    return step


def _probe_edge_cdp(cdp_url: str) -> bool:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    try:
        with httpx.Client(trust_env=False, timeout=1.5) as client:
            resp = client.get(version_url)
            return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def _run_edge_takeover_step(
    db: Database,
    *,
    cdp_url: str = "http://127.0.0.1:9222",
    snapshot_dir: Path | None = None,
    edge_sweep: bool = False,
    max_scrolls: int = 12,
    max_pages: int = 2,
) -> dict[str, Any]:
    """Capture jobs from open Edge 9222 CDP tabs (and optional portal sweep) when available."""
    if not _probe_edge_cdp(cdp_url):
        return {
            "active": False,
            "skipped": True,
            "cdp_url": cdp_url,
            "reason": "edge_cdp_not_detected",
        }

    try:
        from playwright.sync_api import Error as PlaywrightError
    except ImportError:  # pragma: no cover
        PlaywrightError = RuntimeError

    step: dict[str, Any] = {
        "active": True,
        "skipped": False,
        "cdp_url": cdp_url,
        "tabs_extracted": 0,
        "tabs_inserted": 0,
        "tabs_updated": 0,
        "sweep_extracted": 0,
        "sweep_inserted": 0,
        "sweep_updated": 0,
        "errors": [],
    }
    try:
        tab_res = collect_from_open_edge_cdp(
            cdp_url=cdp_url,
            site_filter="auto",
            save_snapshot_dir=snapshot_dir,
            max_scrolls=max_scrolls,
            max_pages=max_pages,
            exclude_social=True,
        )
        tab_jobs = tab_res.get("jobs") or []
        counts = db.upsert_jobs(tab_jobs)
        step["tabs"] = tab_res.get("tabs") or []
        step["tabs_extracted"] = len(tab_jobs)
        step["tabs_inserted"] = counts["inserted"]
        step["tabs_updated"] = counts["updated"]
    except (PlaywrightError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
        step["errors"].append(f"takeover_tabs: {exc}")

    if edge_sweep:
        ins = 0
        upd = 0

        def _on_batch(batch_jobs: list[dict[str, Any]]) -> None:
            nonlocal ins, upd
            c = db.upsert_jobs(batch_jobs)
            ins += c["inserted"]
            upd += c["updated"]

        try:
            sw_res = collect_portal_sweep_cdp(
                cdp_url=cdp_url,
                site_filter="all",
                save_snapshot_dir=snapshot_dir,
                max_scrolls=min(max_scrolls, 8),
                exclude_social=True,
                on_batch=_on_batch,
            )
            step["sweep_queries"] = len(sw_res.get("queries") or [])
            step["sweep_extracted"] = len(sw_res.get("jobs") or [])
            step["sweep_inserted"] = ins
            step["sweep_updated"] = upd
        except (PlaywrightError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            step["errors"].append(f"takeover_sweep: {exc}")

    return step


def run_daily_cycle(
    db: Database,
    *,
    cfg: UserConfig | None = None,
    output_root: Path | None = None,
    prompts_root: Path | None = None,
    sync_sources: bool = True,
    sync_edge: bool = True,
    cdp_url: str = "http://127.0.0.1:9222",
    edge_sweep: bool = False,
    run_prefilter: bool = True,
    run_llm: bool = True,
    match_limit: int = 15,
    package_limit: int = 6,
    job_type: str = "all",
    allow_nationwide: bool = False,
    stale_days: int = 7,
    deadline_days: int = 7,
    send_email: bool = False,
    send_reminder: bool = False,
    sync_relay: bool = True,
    llm_provider: LLMProvider | None = None,
    refresh_progress: bool = True,
) -> dict[str, Any]:
    """Execute one auditable daily cycle: public+Edge sync -> cleanup -> prefilter/Stage 2 -> Stage 5."""
    resolved_cfg = cfg or load_user_config()
    root = get_project_root()
    resolved_output = output_root or (root / "output")
    resolved_prompts = prompts_root or (root / "prompts")

    db.init_schema()
    run_id = db.start_run("daily_cycle")
    steps: dict[str, Any] = {}

    try:
        if sync_sources:
            steps["sync"] = _run_public_sync_step(db, resolved_cfg)
        else:
            steps["sync"] = {"skipped": True}

        if sync_edge:
            steps["edge_takeover"] = _run_edge_takeover_step(
                db,
                cdp_url=cdp_url,
                snapshot_dir=root / "data" / "inbox",
                edge_sweep=edge_sweep,
            )
        else:
            steps["edge_takeover"] = {"skipped": True}

        steps["cleanup_restricted"] = cleanup_restricted_university_jobs(db)

        if run_prefilter:
            candidates_with_meta, pf_stats = select_prefilter_candidates(
                db,
                resolved_cfg,
                limit=match_limit,
                allow_nationwide=allow_nationwide,
                mark_filtered_out=False,
                job_type_filter=job_type,
            )
            steps["prefilter"] = pf_stats
        else:
            candidates_with_meta = []
            steps["prefilter"] = {"skipped": True}

        stage2_summary: dict[str, Any] = {"skipped": not run_llm, "packages_built": 0}
        if run_llm:
            master_row = db.get_latest_master_version()
            if master_row is None:
                stage2_summary = {"skipped": True, "reason": "missing_master_version", "packages_built": 0}
            else:
                profile = MasterProfile.model_validate_json(master_row["profile_json"])
                qa_bank = QABank.model_validate_json(master_row["qa_bank_json"])
                master_id = int(master_row["id"])
                provider = llm_provider or build_llm_provider(resolved_cfg, project_root=root)

                from ..company_check import filter_and_verify_prefilter_candidates

                candidate_jobs, cc_stats = filter_and_verify_prefilter_candidates(
                    db, resolved_cfg, candidates_with_meta, root=root
                )

                match_stats = run_match_batch(
                    db=db,
                    cfg=resolved_cfg,
                    llm=provider,
                    prompts_root=resolved_prompts,
                    candidates=candidate_jobs,
                    master_version_id=master_id,
                    profile=profile,
                )
                pending_pairs = db.get_matches_needing_packages(
                    master_version_id=master_id,
                    min_score=resolved_cfg.scoring.min_score_for_package,
                    limit=package_limit,
                )
                built_count = 0
                for job_dict, match_row in pending_pairs:
                    build_package_for_match(
                        db=db,
                        cfg=resolved_cfg,
                        llm=provider,
                        prompts_root=resolved_prompts,
                        output_root=resolved_output,
                        job=job_dict,
                        match_row=match_row,
                        master_version_id=master_id,
                        profile=profile,
                        qa_bank=qa_bank,
                    )
                    built_count += 1

                stage2_summary = {
                    "skipped": False,
                    "company_check": cc_stats,
                    "match": {k: v for k, v in match_stats.items() if k != "high_score_match_ids"},
                    "packages_built": built_count,
                }
        steps["stage2"] = stage2_summary

        if sync_relay and resolved_cfg.cloud_relay.enabled:
            from ..cloud_relay import pull_and_apply_relay_actions

            steps["relay_pull"] = pull_and_apply_relay_actions(db, resolved_cfg, project_root=root)
        else:
            steps["relay_pull"] = {"status": "skipped"}

        digest = build_daily_digest(
            db,
            output_dir=resolved_output / "digest",
            min_score=resolved_cfg.scoring.min_score_for_package,
            top_n=resolved_cfg.scoring.daily_top_n,
            cfg=resolved_cfg,
        )
        steps["digest"] = {
            "digest_path": digest["digest_path"],
            "packages_count": digest["packages_count"],
        }

        if sync_relay and resolved_cfg.cloud_relay.enabled:
            from ..cloud_relay import push_packages_to_relay

            steps["relay_push"] = push_packages_to_relay(
                db,
                resolved_cfg,
                limit=resolved_cfg.scoring.daily_top_n or 20,
                project_root=root,
            )
        else:
            steps["relay_push"] = {"status": "skipped"}

        delivery = prepare_delivery_bundles(db, output_root=resolved_output, enrich_ncss=False)
        steps["delivery"] = {
            "prepared_count": delivery["prepared_count"],
            "checklist_path": delivery["checklist_path"],
        }

        reminders = collect_reminders(db, deadline_days=deadline_days, stale_days=stale_days)
        steps["reminders"] = {
            "total_alerts": reminders["total_alerts"],
            "summary_text": reminders["summary_text"],
        }

        report = build_weekly_report(
            db,
            output_dir=resolved_output / "reports",
            days=7,
            stale_days=stale_days,
            write_files=True,
        )
        steps["weekly_report"] = {
            "report_md_path": report["report_md_path"],
            "report_json_path": report["report_json_path"],
        }

        email_html = render_daily_email_html(digest=digest, reminders=reminders, report=report)
        email_html_path = resolved_output / "digest" / f"daily_email_{digest['date']}.html"
        email_html_path.write_text(email_html, encoding="utf-8")
        steps["digest"]["email_html_path"] = str(email_html_path)

        top_names = [f"{p['company']}·{p['title']}({p['score']}分)" for p in digest.get("packages", [])[:3]]
        notify_summary = (
            f"精选待选 {digest['packages_count']} 份（{reminders['summary_text']}）"
            + (f" · 优先看：{' / '.join(top_names)}" if top_names else "")
        )
        should_notify = (
            send_email
            or send_reminder
            or stage2_summary.get("packages_built", 0) > 0
            or reminders["total_alerts"] > 0
        )
        if should_notify:
            email_body = (
                f"{report['markdown']}\n---\n"
                f"## 每日简报文件\n`{digest['digest_path']}`\n"
            )
            notify_res = dispatch_notification(
                db,
                resolved_cfg,
                title=f"今日求职推荐与提醒（待选 {digest['packages_count']} 份）",
                body=notify_summary,
                category="daily_digest",
                level="urgent" if reminders["total_alerts"] > 0 else "info",
                action_tab="detail" if digest["packages_count"] > 0 else "insights",
                payload={"date": digest["date"], "packages_count": digest["packages_count"]},
                email_subject=f"[Job-auto] 每日求职汇总与提醒（{digest['date']}）",
                body_text=email_body if (send_email or send_reminder) else notify_summary,
                html_body=email_html if (send_email or send_reminder) else None,
                force_email=bool(send_email),
                email_sender=send_qq_email_digest,
                project_root=root,
            )
            steps["notification"] = notify_res
            steps["email"] = notify_res.get("email", {})
        elif send_email:
            steps["email"] = {"status": "skipped"}

        db.finish_run(run_id, status="completed", stats=steps)
        if refresh_progress and db.db_path.resolve() == (root / "data" / "job_agent.db").resolve():
            update_progress_artifacts(db_path=db.db_path)

        return {
            "status": "ok",
            "run_id": run_id,
            "steps": steps,
            "reminders": reminders,
            "report_md_path": report["report_md_path"],
            "digest_path": digest["digest_path"],
        }
    except Exception as exc:
        db.finish_run(run_id, status="failed", stats=steps, error_log=str(exc))
        raise

"""Stage 3 local FastAPI review workbench (/review) for human-in-the-loop approval."""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from ..config import get_code_root, get_project_root, load_user_config
from ..db import Database
from ..inbox_server import IngestPageRequest, get_inbox_health, ingest_extension_page
from ..launcher import bootstrap_workspace, collect_system_status
from ..notifications import dispatch_notification
from ..progress import collect_live_db_metrics, default_progress_spec, render_progress_html
from ..settings_store import (
    configure_daily_email_schedule,
    import_resume_artifact,
    read_safe_app_settings,
    save_app_settings,
)
from . import workbench_ui as _workbench_ui_mod


class DecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject|later)$")
    reason: str = ""


class ApplicationStatusRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    notes: str | None = None


class ResumeImportRequest(BaseModel):
    filename: str = "resume.txt"
    content_text: str | None = None
    content_base64: str | None = None


class ScheduleUpdateRequest(BaseModel):
    enabled: bool = True
    send_time: str = "16:00"


class MarkNotificationsReadRequest(BaseModel):
    ids: list[int] | None = None


def create_review_app(
    *,
    db_path: Path | None = None,
    output_root: Path | None = None,
) -> FastAPI:
    """Create the Stage 3 local human-review FastAPI application."""
    root = get_project_root()
    resolved_db = db_path or (root / "data" / "job_agent.db")
    resolved_output = output_root or (root / "output")
    cfg = load_user_config()
    db = Database(resolved_db)
    db.init_schema()

    app = FastAPI(title="Job-auto Stage 3 Review Workbench", version="1.5.0-demo")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "db": str(resolved_db)}

    @app.get("/api/health")
    @app.get("/api/inbox/health")
    def inbox_health() -> dict[str, Any]:
        return get_inbox_health(resolved_db)

    @app.post("/api/ingest-page")
    @app.post("/api/inbox/ingest-page")
    def inbox_ingest_page(req: IngestPageRequest) -> dict[str, Any]:
        refresh = resolved_db.resolve() == (root / "data" / "job_agent.db").resolve()
        return ingest_extension_page(
            req,
            db_path=resolved_db,
            inbox_dir=resolved_db.parent / "inbox",
            refresh_progress=refresh,
        )

    @app.get("/progress", response_class=HTMLResponse)
    def progress_page() -> HTMLResponse:
        cur_cfg = load_user_config()
        spec = default_progress_spec()
        live = collect_live_db_metrics(
            resolved_db,
            primary_cities=cur_cfg.preferences.primary_cities,
            secondary_cities=cur_cfg.preferences.secondary_cities,
        )
        return HTMLResponse(render_progress_html({**spec, "live_metrics": live}))

    @app.get("/relay-mobile", response_class=HTMLResponse)
    def relay_mobile_page() -> HTMLResponse:
        from ..relay_mobile_ui import render_relay_mobile_html

        cur_cfg = load_user_config()
        rc = cur_cfg.cloud_relay
        default_ep = rc.endpoint_url if (rc.enabled and rc.provider != "none") else ""
        return HTMLResponse(
            render_relay_mobile_html(
                default_endpoint=default_ep,
                default_pairing_id=rc.pairing_id or "",
            ),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/system/status")
    def api_system_status() -> dict[str, Any]:
        return collect_system_status(root=root, db_path=resolved_db)

    @app.post("/api/system/bootstrap")
    def api_system_bootstrap() -> dict[str, Any]:
        return bootstrap_workspace(root=root, db_path=resolved_db, copy_examples=True)

    @app.post("/api/system/seed-demo")
    def api_system_seed_demo() -> dict[str, Any]:
        from ..demo_seed import seed_demo_workspace

        return seed_demo_workspace(db, output_root=resolved_output)

    @app.get("/api/system/settings")
    def api_get_system_settings() -> dict[str, Any]:
        return read_safe_app_settings(root=root, db_path=resolved_db)

    @app.post("/api/system/settings")
    def api_save_system_settings(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return save_app_settings(payload, root=root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/relay/status")
    def api_relay_status() -> dict[str, Any]:
        from ..cloud_relay import build_relay_client

        cur_cfg = load_user_config()
        client = build_relay_client(cur_cfg.cloud_relay, project_root=root)
        return {
            "status": "ok",
            "enabled": cur_cfg.cloud_relay.enabled,
            "provider": cur_cfg.cloud_relay.provider,
            "fallback_to_email": cur_cfg.cloud_relay.auto_fallback_to_email,
            **client.health(),
        }

    @app.post("/api/relay/sync-preview")
    def api_relay_sync_preview() -> dict[str, Any]:
        from ..cloud_relay import run_relay_sync_preview

        cur_cfg = load_user_config()
        pkgs = db.list_packages_for_review(
            decision_filter="all",
            job_type_filter="all",
            min_score=0,
            limit=10,
        )
        summary = [
            {
                "id": p.get("package_id") or p.get("id"),
                "company": p.get("company"),
                "title": p.get("title"),
                "score": p.get("score"),
                "job_type": p.get("job_type"),
            }
            for p in pkgs
        ]
        return run_relay_sync_preview(cur_cfg, jobs_summary=summary, project_root=root)

    @app.post("/api/relay/push")
    def api_relay_push(limit: int = 20, decision_filter: str = "pending") -> dict[str, Any]:
        from ..cloud_relay import push_packages_to_relay

        cur_cfg = load_user_config()
        return push_packages_to_relay(
            db,
            cur_cfg,
            limit=limit,
            decision_filter=decision_filter,
            project_root=root,
        )

    @app.post("/api/relay/pull")
    def api_relay_pull() -> dict[str, Any]:
        from ..cloud_relay import pull_and_apply_relay_actions

        cur_cfg = load_user_config()
        return pull_and_apply_relay_actions(db, cur_cfg, project_root=root)

    def _safe_stub_pid(raw: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(raw or "").strip())
        return cleaned[:96] or "demo-pair-local"

    @app.get("/api/relay/stub/health")
    def api_relay_stub_health() -> dict[str, Any]:
        from ..cloud_relay import LocalLoopbackRelayStub

        return LocalLoopbackRelayStub(root / "local" / "relay_stub").health()

    @app.get("/api/relay/stub/pull-batch")
    def api_relay_stub_pull_batch(pairing_id: str = "demo-pair-local") -> dict[str, Any]:
        from ..cloud_relay import LocalLoopbackRelayStub

        return LocalLoopbackRelayStub(root / "local" / "relay_stub").pull_batch(
            _safe_stub_pid(pairing_id)
        )

    @app.post("/api/relay/stub/push-batch")
    def api_relay_stub_push_batch(payload: dict[str, Any]) -> dict[str, Any]:
        from ..cloud_relay import LocalLoopbackRelayStub

        env = dict(payload.get("envelope") or payload)
        env["pairing_id"] = _safe_stub_pid(str(env.get("pairing_id") or ""))
        return LocalLoopbackRelayStub(root / "local" / "relay_stub").push_batch(env)

    @app.post("/api/relay/stub/ack-actions")
    def api_relay_stub_ack_actions(payload: dict[str, Any]) -> dict[str, Any]:
        from ..cloud_relay import LocalLoopbackRelayStub

        env = dict(payload.get("envelope") or payload)
        env["pairing_id"] = _safe_stub_pid(str(env.get("pairing_id") or ""))
        return LocalLoopbackRelayStub(root / "local" / "relay_stub").ack_actions(env)

    @app.get("/api/relay/stub/pull-actions")
    def api_relay_stub_pull_actions(pairing_id: str = "demo-pair-local") -> dict[str, Any]:
        from ..cloud_relay import LocalLoopbackRelayStub

        return LocalLoopbackRelayStub(root / "local" / "relay_stub").pull_actions(
            _safe_stub_pid(pairing_id)
        )

    @app.post("/api/system/import-resume")
    def api_import_resume(req: ResumeImportRequest) -> dict[str, Any]:
        try:
            return import_resume_artifact(
                filename=req.filename,
                content_text=req.content_text,
                content_base64=req.content_base64,
                db_path=resolved_db,
                root=root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/system/test-llm")
    def api_test_llm() -> dict[str, Any]:
        from ..llm.openai_compat import test_llm_connection

        return test_llm_connection(load_user_config(), project_root=root)

    @app.post("/api/system/test-email")
    def api_test_email() -> dict[str, Any]:
        from .digest import send_email_digest

        cur_cfg = load_user_config()
        try:
            return send_email_digest(
                cur_cfg,
                subject="[Job-auto] 邮箱连通测试邮件",
                body_text="你好，这是一封来自 Job-auto 设置向导的测试邮件。说明你的 SMTP 发件配置已生效！",
                html_body="<div style='font-family:sans-serif;padding:16px;border:1px solid #e2e8f0;border-radius:10px;'><h3>Job-auto 邮箱配置测试成功</h3><p>当你看到这封邮件时，每日求职简报的 SMTP 通知通道已完全可用。</p></div>",
            )
        except OSError as exc:
            return {"status": "error", "error": str(exc)}

    @app.get("/api/system/schedule")
    def api_get_schedule() -> dict[str, Any]:
        from ..settings_store import query_daily_email_schedule

        return query_daily_email_schedule()

    @app.post("/api/system/schedule")
    def api_set_schedule(req: ScheduleUpdateRequest) -> dict[str, Any]:
        try:
            return configure_daily_email_schedule(
                enabled=req.enabled,
                send_time=req.send_time,
                root=root,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/system/launch-browser")
    def api_system_launch_browser() -> dict[str, Any]:
        from ..launcher import launch_cdp_browser

        return launch_cdp_browser(root=root)

    @app.get("/api/notifications")
    def api_list_notifications(unread_only: bool = False, limit: int = 30) -> dict[str, Any]:
        return {
            "status": "ok",
            "unread_count": db.count_unread_notifications(),
            "items": db.list_notifications(unread_only=unread_only, limit=limit),
        }

    @app.post("/api/notifications/read")
    def api_mark_notifications_read(req: MarkNotificationsReadRequest) -> dict[str, Any]:
        updated = db.mark_notifications_read(req.ids)
        return {
            "status": "ok",
            "marked": updated,
            "unread_count": db.count_unread_notifications(),
        }

    @app.post("/api/notifications/test")
    def api_test_app_notification() -> dict[str, Any]:
        cur_cfg = load_user_config()
        res = dispatch_notification(
            db,
            cur_cfg,
            title="Job-auto 测试提醒：发现高分推荐岗位",
            body="这是一条独立 App 测试消息。优先通过桌面系统弹窗与应用内消息中心通知你，仅在不可用时才降级邮件。",
            category="system",
            level="info",
            action_tab="detail",
            force_email=False,
            project_root=root,
        )
        return {"status": "ok", **res}

    @app.get("/", response_class=HTMLResponse)
    @app.get("/review", response_class=HTMLResponse)
    def review_page() -> HTMLResponse:
        # Reload workbench_ui on request so UI edits appear immediately without hunting background sidecars.
        importlib.reload(_workbench_ui_mod)
        return HTMLResponse(_workbench_ui_mod.REVIEW_HTML, headers={"Cache-Control": "no-store"})

    @app.get("/api/packages")
    def api_list_packages(
        decision: str = "all",
        job_type: str = "all",
        min_score: int = 0,
    ) -> dict[str, Any]:
        all_for_decision = db.list_packages_for_review(
            decision_filter=decision,
            job_type_filter="all",
            min_score=min_score,
            limit=300,
        )
        campus_count = sum(1 for p in all_for_decision if p.get("job_type") != "实习")
        intern_count = sum(1 for p in all_for_decision if p.get("job_type") == "实习")
        pkgs = db.list_packages_for_review(
            decision_filter=decision,
            job_type_filter=job_type,
            min_score=min_score,
            limit=200,
        )
        apps = db.list_applications(limit=200)
        return {
            "packages": pkgs,
            "applications_count": len(apps),
            "campus_count": campus_count,
            "intern_count": intern_count,
        }

    @app.get("/api/packages/{package_id}")
    def api_package_detail(package_id: int) -> dict[str, Any]:
        detail = db.get_package_detail(package_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Package not found")
        return detail

    @app.get("/api/packages/{package_id}/pdf")
    def api_package_pdf(package_id: int, download: bool = False) -> FileResponse:
        detail = db.get_package_detail(package_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Package not found")
        pdf_path = Path(detail.get("resume_pdf_path") or "").resolve()
        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=404, detail="PDF file not found")
        if download:
            company_name = str(detail.get("company") or "").strip()
            safe_company = re.sub(r'[\\/:*?"<>|]+', "_", company_name).strip("_ ")
            safe_name = f"{safe_company}.pdf" if safe_company else "resume.pdf"
            return FileResponse(
                path=str(pdf_path),
                media_type="application/pdf",
                filename=safe_name,
                content_disposition_type="attachment",
            )
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name,
            content_disposition_type="inline",
        )

    @app.post("/api/packages/{package_id}/decision")
    def api_record_decision(package_id: int, req: DecisionRequest) -> dict[str, Any]:
        from .digest import resolve_delivery_mode

        try:
            detail = db.get_package_detail(package_id)
            if detail is None:
                raise HTTPException(status_code=404, detail="Package not found")
            channel = str(detail.get("apply_channel") or "unknown")
            mode = resolve_delivery_mode(cfg, channel)
            result = db.record_decision(
                package_id=package_id,
                decision=req.decision,
                reason=req.reason,
                default_mode=mode,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", **result}

    @app.get("/api/applications")
    def api_list_applications(
        status: str | None = None,
        job_type: str | None = None,
    ) -> dict[str, Any]:
        return {"applications": db.list_applications(status=status, job_type=job_type, limit=200)}

    @app.get("/api/applications/summary")
    def api_applications_summary(stale_days: int = 7) -> dict[str, Any]:
        from ..stage4 import summarize_delivery_tracker

        return summarize_delivery_tracker(db, stale_days=stale_days)

    @app.post("/api/export-autofill")
    def api_export_autofill() -> dict[str, Any]:
        from ..stage4 import export_autofill_profile

        res = export_autofill_profile(cfg=load_user_config(), db=db)
        return {"status": "ok", **res}

    @app.get("/api/autofill/bundle")
    def api_autofill_bundle(limit: int = 12) -> dict[str, Any]:
        from ..stage4 import export_autofill_profile

        cur_cfg = load_user_config()
        export_res = export_autofill_profile(cfg=cur_cfg, db=db)
        backup_path = Path(str(export_res.get("backup_path") or ""))
        profiles: list[dict[str, Any]] = []
        if backup_path.is_file():
            raw = json.loads(backup_path.read_text(encoding="utf-8"))
            profiles = list(((raw.get("data") or {}).get("resumeProfiles")) or [])

        bounded = max(1, min(int(limit), 30))
        pkgs = db.list_packages_for_review(
            decision_filter="approved", job_type_filter="all", min_score=0, limit=bounded
        )
        if not pkgs:
            pkgs = db.list_packages_for_review(
                decision_filter="pending", job_type_filter="all", min_score=0, limit=bounded
            )
        pkg_summaries = [
            {
                "package_id": int(p["package_id"]),
                "company": p.get("company") or "",
                "title": p.get("title") or "",
                "job_type": p.get("job_type") or "",
                "score": int(p.get("score") or 0),
                "url": p.get("url") or "",
                "greeting": p.get("greeting") or "",
                "qa": p.get("qa") or {},
            }
            for p in pkgs
        ]
        return {
            "status": "ok",
            "profiles": profiles,
            "packages": pkg_summaries,
            "basic_fields_filled": export_res.get("basic_fields_filled", 0),
        }

    @app.post("/api/prepare-delivery")
    def api_prepare_delivery(enrich: bool = True) -> dict[str, Any]:
        from ..stage4 import prepare_delivery_bundles

        res = prepare_delivery_bundles(db, output_root=resolved_output, enrich_ncss=enrich)
        return {
            "status": "ok",
            "ready_root": res["ready_root"],
            "checklist_path": res["checklist_path"],
            "prepared_count": res["prepared_count"],
            "enriched_count": res["enriched_count"],
            "staged_pdfs": res["staged_pdfs"],
        }

    @app.post("/api/applications/{application_id}/open-edge")
    def api_open_application_in_edge(application_id: int) -> dict[str, Any]:
        from ..stage4 import open_application_in_edge

        rows = [a for a in db.list_applications(limit=500) if int(a["id"]) == application_id]
        if not rows:
            raise HTTPException(status_code=404, detail="Application not found")
        target = str(rows[0].get("apply_target") or rows[0].get("url") or "").strip()
        return open_application_in_edge(target)

    @app.post("/api/applications/{application_id}/status")
    def api_update_application(application_id: int, req: ApplicationStatusRequest) -> dict[str, Any]:
        try:
            res = db.update_application_status(
                application_id=application_id,
                status=req.status,
                notes=req.notes,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "ok", **res}

    @app.post("/api/export-queue")
    def api_export_queue() -> dict[str, Any]:
        from .digest import export_approved_queue

        res = export_approved_queue(db, output_dir=resolved_output / "digest")
        return {"status": "ok", **res}

    @app.post("/api/digest")
    def api_digest() -> dict[str, Any]:
        from .digest import build_daily_digest

        cur_cfg = load_user_config()
        res = build_daily_digest(
            db,
            output_dir=resolved_output / "digest",
            min_score=cur_cfg.scoring.min_score_for_package,
            top_n=cur_cfg.scoring.daily_top_n,
        )
        res.pop("digest_markdown", None)
        return {"status": "ok", **res}

    @app.get("/api/stage5/overview")
    def api_stage5_overview(
        days: int = 7,
        deadline_days: int = 7,
        stale_days: int = 7,
    ) -> dict[str, Any]:
        from ..stage5 import build_weekly_report, collect_reminders

        reminders = collect_reminders(db, deadline_days=deadline_days, stale_days=stale_days)
        report = build_weekly_report(
            db,
            days=days,
            stale_days=stale_days,
            write_files=False,
        )
        report.pop("markdown", None)
        return {"status": "ok", "reminders": reminders, "weekly_report": report}

    @app.post("/api/stage5/weekly-report")
    def api_stage5_weekly_report(days: int = 7, stale_days: int = 7) -> dict[str, Any]:
        from ..stage5 import build_weekly_report

        report = build_weekly_report(
            db,
            output_dir=resolved_output / "reports",
            days=days,
            stale_days=stale_days,
            write_files=True,
        )
        report.pop("markdown", None)
        return {"status": "ok", **report}

    def _resolve_prompts_root() -> Path:
        code_prompts = get_code_root() / "prompts"
        if code_prompts.is_dir():
            return code_prompts
        return root / "prompts"

    @app.post("/api/stage5/refresh-cycle")
    def api_stage5_refresh_cycle() -> dict[str, Any]:
        from ..stage5 import run_daily_cycle

        cur_cfg = load_user_config()
        res = run_daily_cycle(
            db,
            cfg=cur_cfg,
            output_root=resolved_output,
            prompts_root=_resolve_prompts_root(),
            sync_sources=False,
            sync_edge=False,
            run_prefilter=False,
            run_llm=False,
            send_email=False,
            sync_relay=False,
        )
        return res

    @app.post("/api/stage5/expand-only")
    def api_stage5_expand_only() -> dict[str, Any]:
        from ..stage5 import run_daily_cycle

        cur_cfg = load_user_config()
        return run_daily_cycle(
            db,
            cfg=cur_cfg,
            output_root=resolved_output,
            prompts_root=_resolve_prompts_root(),
            sync_sources=True,
            sync_edge=True,
            edge_sweep=False,
            run_prefilter=False,
            run_llm=False,
            send_email=False,
        )

    @app.post("/api/stage5/run-screen")
    def api_stage5_run_screen() -> dict[str, Any]:
        from ..stage5 import run_daily_cycle

        cur_cfg = load_user_config()
        return run_daily_cycle(
            db,
            cfg=cur_cfg,
            output_root=resolved_output,
            prompts_root=_resolve_prompts_root(),
            sync_sources=False,
            sync_edge=False,
            run_prefilter=True,
            run_llm=True,
            send_email=False,
        )

    @app.post("/api/stage5/send-reminder")
    @app.post("/api/stage5/send-email")
    def api_stage5_send_email() -> dict[str, Any]:
        from ..stage5 import run_daily_cycle

        cur_cfg = load_user_config()
        return run_daily_cycle(
            db,
            cfg=cur_cfg,
            output_root=resolved_output,
            prompts_root=_resolve_prompts_root(),
            sync_sources=False,
            sync_edge=False,
            run_prefilter=False,
            run_llm=False,
            send_email=False,
            send_reminder=True,
        )

    return app

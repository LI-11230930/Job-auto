"""Tests for Stage 5 reminders, weekly analytics report, and daily-cycle orchestration."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from job_agent.cli import main as cli_main
from job_agent.config import UserConfig
from job_agent.db import Database
from job_agent.llm import (
    FallbackLLMProvider,
    OpenAICompatibleProvider,
    PromptAsset,
    build_llm_provider,
)
from job_agent.progress import update_progress_artifacts
from job_agent.stage3.review_server import create_review_app
from job_agent.stage5 import (
    build_weekly_report,
    collect_reminders,
    list_recent_runs,
    parse_deadline_date,
    run_daily_cycle,
)


def _seed_stage5_db(tmp_path: Path) -> tuple[Path, Database]:
    db_path = tmp_path / "stage5.db"
    db = Database(db_path)
    db.init_schema()
    master_id = db.upsert_master_version(version_tag="v1", profile_json="{}", qa_bank_json="{}")
    db.upsert_jobs(
        [
            {
                "source": "zhaopin",
                "source_job_id": "z1",
                "company": "晋城示范财务公司",
                "title": "财务管培生",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "会计学 财务管理",
                "url": "https://www.zhaopin.com/jobdetail/z1.htm",
                "apply_channel": "third_party",
                "apply_target": "https://www.zhaopin.com/jobdetail/z1.htm",
                "deadline": "2026-11-16",
                "industry": "制造业",
                "status": "active",
                "dedup_hash": "h-z1",
                "priority_rank": 1,
            },
            {
                "source": "shixiseng",
                "source_job_id": "s1",
                "company": "青岛示范审计所",
                "title": "审计实习生",
                "cities": ["青岛"],
                "job_type": "实习",
                "jd_text": "审计 实习",
                "url": "https://www.shixiseng.com/intern/s1",
                "apply_channel": "third_party",
                "apply_target": "https://www.shixiseng.com/intern/s1",
                "deadline": "2026年11月20日",
                "industry": "专业服务",
                "status": "active",
                "dedup_hash": "h-s1",
                "priority_rank": 1,
            },
            {
                "source": "zhaopin",
                "source_job_id": "z2",
                "company": "异地销售公司",
                "title": "财务专员",
                "cities": ["济南"],
                "job_type": "校招",
                "jd_text": "核算",
                "url": "https://www.zhaopin.com/jobdetail/z2.htm",
                "apply_channel": "third_party",
                "apply_target": "https://www.zhaopin.com/jobdetail/z2.htm",
                "deadline": "长期有效",
                "industry": "贸易",
                "status": "active",
                "dedup_hash": "h-z2",
                "priority_rank": 1,
            },
        ]
    )
    with db.connect() as conn:
        jids = [int(r["id"]) for r in conn.execute("SELECT id FROM jobs ORDER BY id").fetchall()]

    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%stage5\n")

    pkg_ids: list[int] = []
    for idx, jid in enumerate(jids):
        score = 92 - idx * 4
        mid = db.insert_match(
            job_id=jid,
            master_version_id=master_id,
            rule_pass=True,
            score=score,
            reasons=[{"dimension": "专业", "score": 28, "evidence": "会计学"}],
            gaps=[],
            strategy={},
            model="test",
            prompt_version="v1",
        )
        pkg_id = db.insert_package(
            job_id=jid,
            match_id=mid,
            master_version_id=master_id,
            resume_pdf_path=str(pdf_path),
            diff_md_path="",
            qa={"请用 200-300 字做一下自我介绍": "具备审计与ERP实训经历。"},
            greeting="您好",
            retry_count=0,
            factcheck_status="pass",
        )
        pkg_ids.append(pkg_id)

    dec1 = db.record_decision(package_id=pkg_ids[0], decision="approve")
    app1 = int(dec1["application_id"])
    old_ts = (datetime.now(UTC) - timedelta(days=9)).isoformat(timespec="seconds")
    with db.connect() as conn:
        conn.execute(
            "UPDATE applications SET status = '已投递', submitted_at = ?, updated_at = ? WHERE id = ?",
            (old_ts, old_ts, app1),
        )

    dec2 = db.record_decision(package_id=pkg_ids[1], decision="approve")
    app2 = int(dec2["application_id"])
    db.update_application_status(application_id=app2, status="面试中", notes="周五14:00一面")

    db.record_decision(package_id=pkg_ids[2], decision="reject", reason="需加班出差较多")
    return db_path, db


def test_parse_deadline_date_variants() -> None:
    assert parse_deadline_date("2026-11-20") == date(2026, 11, 20)
    assert parse_deadline_date("2026/11/5") == date(2026, 11, 5)
    assert parse_deadline_date("截止至2026年12月01日") == date(2026, 12, 1)
    assert parse_deadline_date("长期招满即止") is None


def test_collect_reminders_and_weekly_report(tmp_path: Path) -> None:
    _, db = _seed_stage5_db(tmp_path)
    today = date(2026, 11, 13)

    rem = collect_reminders(db, deadline_days=8, stale_days=7, today=today)
    assert len(rem["urgent_deadlines"]) == 1
    assert rem["urgent_deadlines"][0]["company"] == "青岛示范审计所"
    assert rem["urgent_deadlines"][0]["days_left"] == 7
    assert len(rem["stale_followups"]) == 1
    assert rem["stale_followups"][0]["company"] == "晋城示范财务公司"
    assert len(rem["in_progress_interviews"]) == 1
    assert rem["in_progress_interviews"][0]["status"] == "面试中"

    out_reports = tmp_path / "output" / "reports"
    report = build_weekly_report(db, output_dir=out_reports, days=7, today=today, write_files=True)
    assert report["funnel"]["active_jobs"] == 3
    assert report["funnel"]["decisions"]["approve"] == 2
    assert report["funnel"]["decisions"]["reject"] == 1
    assert report["funnel"]["rates"]["approval_rate_pct"] == 66.7
    assert report["reject_reasons"] == [{"reason": "需加班出差较多", "count": 1}]
    assert any("需加班出差较多" in tip for tip in report["tuning_suggestions"])
    assert Path(report["report_md_path"]).is_file()
    loaded_json = json.loads(Path(report["report_json_path"]).read_text(encoding="utf-8"))
    assert loaded_json["funnel"]["applications_by_track"]["campus"]["submitted"] == 1
    assert loaded_json["funnel"]["applications_by_track"]["intern"]["in_progress"] == 1


def test_daily_cycle_cli_and_workbench_stage5_endpoints(tmp_path: Path) -> None:
    db_path, db = _seed_stage5_db(tmp_path)
    out_root = tmp_path / "output"
    res = run_daily_cycle(
        db,
        cfg=UserConfig(),
        output_root=out_root,
        sync_sources=False,
        run_llm=False,
        send_email=False,
        refresh_progress=False,
    )
    assert res["status"] == "ok"
    assert res["run_id"] >= 1
    assert Path(res["report_md_path"]).is_file()
    assert Path(res["digest_path"]).is_file()
    runs = list_recent_runs(db, limit=5)
    assert runs and runs[0]["run_type"] == "daily_cycle" and runs[0]["status"] == "completed"

    assert cli_main(["--db", str(db_path), "reminders"]) == 0
    assert cli_main(["--db", str(db_path), "weekly-report"]) == 0
    assert cli_main(["--db", str(db_path), "daily-cycle", "--skip-sync", "--skip-llm"]) == 0

    app = create_review_app(db_path=db_path, output_root=out_root)
    client = TestClient(app)
    r_ov = client.get("/api/stage5/overview")
    assert r_ov.status_code == 200
    assert "reminders" in r_ov.json() and "weekly_report" in r_ov.json()

    r_rep = client.post("/api/stage5/weekly-report")
    assert r_rep.status_code == 200
    assert Path(r_rep.json()["report_md_path"]).is_file()

    r_cyc = client.post("/api/stage5/refresh-cycle")
    assert r_cyc.status_code == 200
    assert r_cyc.json()["status"] == "ok"


def test_openai_compat_fallback_sync_cycle_and_progress_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_FALLBACK_KEY", "sk-test-123456")
    captured_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured_models.append(body["model"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '```json\n{"score": 88, "ok": true}\n```'}}
                ]
            },
        )

    asset = PromptAsset(
        task="test",
        prompt_version="v1",
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.0,
        system_instruction="return json",
        response_schema={"type": "object"},
    )

    class _FailingPrimary:
        def generate_json(self, **_: object) -> dict[str, object]:
            raise RuntimeError("429 quota exhausted")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    compat = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1",
        model="deepseek-chat",
        api_key_env="TEST_FALLBACK_KEY",
        client=client,
    )
    router = FallbackLLMProvider(primary=_FailingPrimary(), fallback=compat)
    out = router.generate_json(asset=asset, payload={"hello": "world"}, model_override="gemini-3.5-flash-lite")
    assert out == {"score": 88, "ok": True}
    assert router.last_used == "fallback"
    assert "429 quota exhausted" in router.last_primary_error
    assert captured_models == ["deepseek-chat"]

    monkeypatch.setenv("FALLBACK_LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("FALLBACK_LLM_MODEL", "deepseek-chat")
    cfg = UserConfig()
    cfg.llm.fallback_enabled = True
    built = build_llm_provider(cfg, project_root=tmp_path)
    assert isinstance(built, FallbackLLMProvider)

    # Also verify run_daily_cycle(sync_sources=True) adapter interfaces cleanly.
    db_path, db = _seed_stage5_db(tmp_path)

    class _StubAdapter:
        source_name = "stub"

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def fetch_jobs(self) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr("job_agent.stage5.daily_cycle.NcssPublicAdapter", _StubAdapter)
    monkeypatch.setattr("job_agent.stage5.daily_cycle.ZhaopinPublicAdapter", _StubAdapter)
    monkeypatch.setattr("job_agent.stage5.daily_cycle.ShixisengPublicAdapter", _StubAdapter)
    cfg.data_sources.campus_site_jobs_path = str(tmp_path / "missing_jobs.json")
    sync_res = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=tmp_path / "output",
        sync_sources=True,
        run_llm=False,
        refresh_progress=False,
    )
    assert sync_res["steps"]["sync"]["errors"] == []

    # Verify progress sync_stages updates all P0..P5 states cleanly without duplicate milestones.
    update_progress_artifacts(
        project_root=tmp_path,
        db_path=db_path,
        milestone_title="Stage 5 验证完成",
        milestone_detail="全流程验证通过",
        test_count=33,
        sync_stages=True,
    )
    update_progress_artifacts(
        project_root=tmp_path,
        db_path=db_path,
        milestone_title="Stage 5 验证完成",
        milestone_detail="全流程验证通过",
        test_count=33,
        sync_stages=True,
    )
    prog_data = json.loads((tmp_path / "local" / "progress_data.json").read_text(encoding="utf-8"))
    assert prog_data["current_stage"] == "stage6"
    assert all(s["state"] == "complete" for s in prog_data["stages"][:6])
    assert [s["code"] + ":" + s["state"] for s in prog_data["stages"][6:]] == [
        "P6:complete",
        "P7:active",
        "P8:complete",
    ]
    assert sum(1 for m in prog_data["milestones"] if m["title"] == "Stage 5 验证完成") == 1


def test_daily_cycle_edge_9222_takeover_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path, db = _seed_stage5_db(tmp_path)
    out_root = tmp_path / "output"
    cfg = UserConfig()

    # Case 1: Edge 9222 not running -> cleanly skipped without failing.
    monkeypatch.setattr("job_agent.stage5.daily_cycle._probe_edge_cdp", lambda _url: False)
    res_off = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=out_root,
        sync_sources=False,
        sync_edge=True,
        run_prefilter=False,
        run_llm=False,
        refresh_progress=False,
    )
    assert res_off["steps"]["edge_takeover"]["active"] is False
    assert res_off["steps"]["edge_takeover"]["skipped"] is True
    assert res_off["steps"]["prefilter"] == {"skipped": True}

    # Case 2: Edge 9222 active -> tabs + optional sweep upsert jobs into DB.
    monkeypatch.setattr("job_agent.stage5.daily_cycle._probe_edge_cdp", lambda _url: True)
    tab_job = {
        "source": "zhipin",
        "source_job_id": "boss-edge-1",
        "company": "晋能示范数字科技",
        "title": "财务运营专员",
        "cities": ["太原"],
        "job_type": "校招",
        "jd_text": "财务 核算",
        "url": "https://www.zhipin.com/job_detail/edge1.html",
        "apply_channel": "third_party",
        "apply_target": "https://www.zhipin.com/job_detail/edge1.html",
        "deadline": "",
        "industry": "能源科技",
        "status": "active",
        "dedup_hash": "h-edge-1",
        "priority_rank": 10,
    }
    sweep_job = {
        "source": "zhaopin",
        "source_job_id": "zp-edge-2",
        "company": "山煤示范财务共享",
        "title": "会计专员",
        "cities": ["太原"],
        "job_type": "校招",
        "jd_text": "共享中心 会计",
        "url": "https://www.zhaopin.com/jobdetail/edge2.htm",
        "apply_channel": "third_party",
        "apply_target": "https://www.zhaopin.com/jobdetail/edge2.htm",
        "deadline": "",
        "industry": "能源",
        "status": "active",
        "dedup_hash": "h-edge-2",
        "priority_rank": 10,
    }
    monkeypatch.setattr(
        "job_agent.stage5.daily_cycle.collect_from_open_edge_cdp",
        lambda **kwargs: {"tabs": [{"site": "zhipin", "extracted": 1}], "jobs": [tab_job]},
    )

    def _fake_sweep(**kwargs: object) -> dict[str, object]:
        cb = kwargs.get("on_batch")
        if callable(cb):
            cb([sweep_job])
        return {"queries": [{"site": "zhaopin", "extracted": 1}], "jobs": [sweep_job]}

    monkeypatch.setattr("job_agent.stage5.daily_cycle.collect_portal_sweep_cdp", _fake_sweep)
    res_on = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=out_root,
        sync_sources=False,
        sync_edge=True,
        edge_sweep=True,
        run_prefilter=False,
        run_llm=False,
        refresh_progress=False,
    )
    edge_step = res_on["steps"]["edge_takeover"]
    assert edge_step["active"] is True
    assert edge_step["tabs_inserted"] == 1
    assert edge_step["sweep_inserted"] == 1
    assert db.count_jobs() == 5

    # CLI flags `--skip-sync --skip-edge --skip-prefilter --skip-llm` work cleanly.
    assert (
        cli_main(
            [
                "--db",
                str(db_path),
                "daily-cycle",
                "--skip-sync",
                "--skip-edge",
                "--skip-prefilter",
                "--skip-llm",
            ]
        )
        == 0
    )

    # Verify daily-cycle email renders HTML and attaches html_body.
    sent_payload: dict[str, object] = {}

    def _fake_send(cfg_arg: UserConfig, *, subject: str, body_text: str, html_body: str | None = None):
        sent_payload["subject"] = subject
        sent_payload["has_html"] = bool(html_body)
        return {"status": "sent", "email_to": "user@qq.com", "port": 465, "has_html": bool(html_body)}

    monkeypatch.setattr("job_agent.stage5.daily_cycle.send_qq_email_digest", _fake_send)
    res_mail = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=out_root,
        sync_sources=False,
        sync_edge=False,
        run_prefilter=False,
        run_llm=False,
        send_email=True,
        refresh_progress=False,
    )
    assert sent_payload["has_html"] is True
    assert res_mail["steps"]["email"]["status"] == "sent"
    assert Path(res_mail["steps"]["digest"]["email_html_path"]).is_file()

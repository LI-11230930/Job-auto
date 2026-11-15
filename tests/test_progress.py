"""Tests for local progress monitor JSON and standalone HTML generation."""

from __future__ import annotations

import json
from pathlib import Path

from job_agent.db import Database
from job_agent.progress import collect_live_db_metrics, update_progress_artifacts
from job_agent.sources.base import compute_dedup_hash


def test_progress_dashboard_renders_live_db_metrics_and_csp(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "user_config.yaml").write_text(
        "preferences:\n"
        "  primary_cities: [\"太原\", \"山西\"]\n"
        "  secondary_cities: [\"济南\", \"青岛\", \"西安\"]\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "data" / "job_agent.db"
    db = Database(db_path)
    db.init_schema()
    db.upsert_jobs(
        [
            {
                "source": "ncss",
                "source_job_id": "N1",
                "company": "中铁三局",
                "title": "财务管理岗",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "财务岗位",
                "url": "https://www.ncss.cn/student/jobs/N1/detail.html",
                "apply_channel": "third_party",
                "apply_target": "https://www.ncss.cn/student/jobs/N1/detail.html",
                "deadline": "",
                "industry": "国企",
                "status": "active",
                "dedup_hash": compute_dedup_hash(
                    company="中铁三局", title="财务管理岗", job_type="校招"
                ),
                "priority_rank": 10,
            },
            {
                "source": "zhaopin",
                "source_job_id": "Z1",
                "company": "海信集团",
                "title": "财务管培生",
                "cities": ["青岛"],
                "job_type": "校招",
                "jd_text": "财务管培",
                "url": "https://www.zhaopin.com/jobdetail/Z1.htm",
                "apply_channel": "third_party",
                "apply_target": "https://www.zhaopin.com/jobdetail/Z1.htm",
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": compute_dedup_hash(
                    company="海信集团", title="财务管培生", job_type="校招"
                ),
                "priority_rank": 10,
            },
        ]
    )
    run_id = db.start_run("ingest_public_ncss")
    db.finish_run(run_id, status="completed", stats={"inserted": 1})

    metrics = collect_live_db_metrics(
        db_path,
        primary_cities=["太原", "山西"],
        secondary_cities=["济南", "青岛", "西安"],
    )
    assert metrics["total_jobs"] == 2
    assert metrics["primary_finance_jobs"] == 1
    assert metrics["secondary_finance_jobs"] == 1
    assert metrics["by_source_bucket"]["ncss"] == 1
    assert metrics["by_source_bucket"]["zhaopin"] == 1

    res = update_progress_artifacts(
        project_root=tmp_path,
        db_path=db_path,
        milestone_title="测试里程碑",
        milestone_detail="验证进度监控 HTML 生成",
        test_count=14,
    )
    html_path = Path(res["html_path"])
    data_path = Path(res["data_path"])
    assert html_path.exists()
    assert data_path.exists()

    html_text = html_path.read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html_text
    assert "connect-src 'none'" in html_text
    assert "测试里程碑" in html_text
    assert "中铁三局" not in html_text  # Summary counts only, no raw secret leak
    assert '"primary_finance_jobs": 1' in html_text

    saved_spec = json.loads(data_path.read_text(encoding="utf-8"))
    assert saved_spec["milestones"][-1]["test_count"] == 14

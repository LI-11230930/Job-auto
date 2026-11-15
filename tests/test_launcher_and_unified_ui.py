"""Tests for one-click workspace bootstrap, unified 8788 server, and system endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from job_agent.cli import main as cli_main
from job_agent.config import DataSourcesConfig
from job_agent.db import Database
from job_agent.launcher import (
    bootstrap_workspace,
    collect_system_status,
    resolve_extension_paths,
)
from job_agent.stage3.review_server import create_review_app


def test_bootstrap_workspace_and_extension_discovery(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".env.example").write_text("GEMINI_API_KEY=demo\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "user_config.example.yaml").write_text(
        "data_sources:\n  campus_site_jobs_path: ''\n",
        encoding="utf-8",
    )
    ext_dir = tmp_path / "extensions" / "job_auto_collector"
    ext_dir.mkdir(parents=True)
    (ext_dir / "manifest.json").write_text('{"manifest_version": 3, "name": "test"}', encoding="utf-8")

    # Pre-existing .env should never be overwritten on re-bootstrap.
    res1 = bootstrap_workspace(root=tmp_path, copy_examples=True)
    assert Path(res1["db_path"]).is_file()
    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "config" / "user_config.yaml").is_file()

    (tmp_path / ".env").write_text("GEMINI_API_KEY=custom_user_value\n", encoding="utf-8")
    res2 = bootstrap_workspace(root=tmp_path, copy_examples=True)
    assert res2["created_files"] == []
    assert "custom_user_value" in (tmp_path / ".env").read_text(encoding="utf-8")

    exts = resolve_extension_paths(root=tmp_path)
    assert exts == [ext_dir.resolve()]

    monkeypatch.setenv("JOB_AUTO_EXTRA_EXTENSIONS", "")
    status = collect_system_status(root=tmp_path, db_path=tmp_path / "data" / "job_agent.db")
    assert status["env_exists"] is True
    assert status["db_exists"] is True
    assert status["extensions"] == [str(ext_dir.resolve())]
    assert DataSourcesConfig().campus_site_jobs_path == ""


def test_unified_workbench_mounts_inbox_progress_and_system_routes(tmp_path: Path) -> None:
    db_path = tmp_path / "unified.db"
    out_dir = tmp_path / "output"
    db = Database(db_path)
    db.init_schema()

    app = create_review_app(db_path=db_path, output_root=out_dir)
    client = TestClient(app)

    # Progress view is served directly inside the unified workbench server.
    prog = client.get("/progress")
    assert prog.status_code == 200
    assert "推进监控台" in prog.text

    # Unified system status endpoint works cleanly.
    sys_res = client.get("/api/system/status")
    assert sys_res.status_code == 200
    assert sys_res.json()["status"] == "ok"

    # Collector extension endpoints are mounted directly on the unified workbench port.
    health = client.get("/api/inbox/health")
    assert health.status_code == 200
    assert health.json()["total_in_db"] == 0

    ingest = client.post(
        "/api/inbox/ingest-page",
        json={
            "url": "https://www.zhipin.com/web/geek/job?query=财务",
            "site": "zhipin",
            "cards": [
                {
                    "title": "财务管培生",
                    "company": "晋能示范集团",
                    "city": "太原",
                    "salary": "8-12K",
                    "tags": ["2027届", "校招"],
                    "url": "https://www.zhipin.com/job_detail/demo-1.html",
                }
            ],
            "exclude_social": True,
        },
    )
    assert ingest.status_code == 200
    payload = ingest.json()
    assert payload["status"] == "ok"
    assert payload["inserted"] == 1
    assert payload["total_in_db"] == 1


def test_cli_doctor_and_setup_on_temp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_test.db"
    assert cli_main(["--db", str(db_path), "setup"]) == 0
    assert db_path.is_file()
    assert cli_main(["--db", str(db_path), "doctor"]) == 0

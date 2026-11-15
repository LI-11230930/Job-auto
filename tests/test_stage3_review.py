"""Tests for Stage 3 FastAPI review workbench, decision queue, digest, and email guard."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from job_agent.config import load_user_config
from job_agent.db import Database
from job_agent.stage3.digest import (
    build_daily_digest,
    render_daily_email_html,
    send_qq_email_digest,
)
from job_agent.stage3.review_server import create_review_app


def _seed_review_db(tmp_path: Path) -> tuple[Path, Path, int]:
    db_path = tmp_path / "review.db"
    db = Database(db_path)
    db.init_schema()
    master_id = db.upsert_master_version(
        version_tag="v1.0",
        profile_json='{"name":"林子轩（示例）"}',
        qa_bank_json='{"items":[]}',
    )
    db.upsert_jobs(
        [
            {
                "source": "ncss",
                "source_job_id": "job-101",
                "company": "太原示范审计事务所",
                "title": "审计助理（2027校招）",
                "cities": ["太原", "山西"],
                "job_type": "校招",
                "jd_text": "负责财务报表审计底稿编制与凭证核对。",
                "url": "https://example.com/job/101",
                "apply_channel": "company_portal",
                "apply_target": "https://example.com/job/101",
                "deadline": "",
                "industry": "会计/审计",
                "status": "active",
                "dedup_hash": "hash-review-101",
                "priority_rank": 1,
            },
            {
                "source": "shixiseng",
                "source_job_id": "job-102",
                "company": "太原数智财务科技有限公司",
                "title": "财务数据分析实习生",
                "cities": ["太原"],
                "job_type": "实习",
                "jd_text": "协助完成Python数据处理与月度报表分析。",
                "url": "https://example.com/job/102",
                "apply_channel": "third_party",
                "apply_target": "https://example.com/job/102",
                "deadline": "",
                "industry": "软件/数据",
                "status": "active",
                "dedup_hash": "hash-review-102",
                "priority_rank": 1,
            },
        ]
    )
    with db.connect() as conn:
        job_ids = [
            int(r[0]) for r in conn.execute("SELECT id FROM jobs ORDER BY id ASC").fetchall()
        ]
    job_id, intern_job_id = job_ids[0], job_ids[1]

    match_id = db.insert_match(
        job_id=job_id,
        master_version_id=master_id,
        rule_pass=True,
        score=94,
        reasons=[{"dimension": "专业匹配", "score": 29, "evidence": "会计学专业+实训匹配"}],
        gaps=["CET-4 未过"],
        strategy={"focus_tags": ["审计"]},
        model="gemini-3.5-flash-lite",
        prompt_version="v1.0",
    )
    intern_match_id = db.insert_match(
        job_id=intern_job_id,
        master_version_id=master_id,
        rule_pass=True,
        score=91,
        reasons=[{"dimension": "技能经历", "score": 14, "evidence": "Python+财务数据处理"}],
        gaps=[],
        strategy={"focus_tags": ["数据分析"]},
        model="gemini-3.5-flash-lite",
        prompt_version="v1.0",
    )

    out_dir = tmp_path / "output"
    pkg_dir = out_dir / "packages" / "101_test"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pkg_dir / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%test\n")
    diff_path = pkg_dir / "diff.md"
    diff_path.write_text("# diff\n- 原句保留", encoding="utf-8")

    pkg_id = db.insert_package(
        job_id=job_id,
        match_id=match_id,
        master_version_id=master_id,
        resume_pdf_path=str(pdf_path),
        diff_md_path=str(diff_path),
        qa={"英语水平": "CET-4 最高分 418 分"},
        greeting="您好，申请贵所审计助理岗位。",
        retry_count=0,
        factcheck_status="pass",
    )
    db.insert_package(
        job_id=intern_job_id,
        match_id=intern_match_id,
        master_version_id=master_id,
        resume_pdf_path=str(pdf_path),
        diff_md_path=str(diff_path),
        qa={"到岗时间": "一周内到岗"},
        greeting="您好，申请贵司财务数据分析实习生岗位。",
        retry_count=0,
        factcheck_status="pass",
    )
    return db_path, out_dir, pkg_id


def test_review_workbench_flow_and_digest(tmp_path: Path, monkeypatch) -> None:
    db_path, out_dir, pkg_id = _seed_review_db(tmp_path)
    app = create_review_app(db_path=db_path, output_root=out_dir)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    review_html = client.get("/review").text
    assert "Job-auto · 智能求职助手 App" in review_html
    assert review_html.index("下载简历") < review_html.index("通过并加入投递队列")
    script_match = re.search(r"<script>(.*?)</script>", review_html, flags=re.DOTALL)
    assert script_match is not None
    js_path = tmp_path / "review.js"
    js_path.write_text(script_match.group(1), encoding="utf-8")
    node_bin = shutil.which("node")
    if node_bin:
        chk = subprocess.run(
            [node_bin, "--check", str(js_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert chk.returncode == 0, chk.stderr

    lst = client.get("/api/packages?decision=pending").json()
    assert len(lst["packages"]) == 2
    assert lst["campus_count"] == 1
    assert lst["intern_count"] == 1

    campus_lst = client.get("/api/packages?decision=pending&job_type=秋招").json()
    assert len(campus_lst["packages"]) == 1
    assert campus_lst["packages"][0]["package_id"] == pkg_id

    intern_lst = client.get("/api/packages?decision=pending&job_type=实习").json()
    assert len(intern_lst["packages"]) == 1
    assert intern_lst["packages"][0]["job_type"] == "实习"

    detail = client.get(f"/api/packages/{pkg_id}").json()
    assert detail["diff_md_text"].startswith("# diff")
    assert detail["pdf_exists"] is True

    pdf_res = client.get(f"/api/packages/{pkg_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers.get("content-disposition", "").startswith("inline")
    assert pdf_res.content.startswith(b"%PDF-1.4")

    dl_res = client.get(f"/api/packages/{pkg_id}/pdf?download=1")
    assert dl_res.status_code == 200
    cd_dl = dl_res.headers.get("content-disposition", "")
    assert cd_dl.startswith("attachment")
    assert "%E5%A4%AA%E5%8E%9F%E7%A4%BA%E8%8C%83%E5%AE%A1%E8%AE%A1%E4%BA%8B%E5%8A%A1%E6%89%80.pdf" in cd_dl

    dec = client.post(
        f"/api/packages/{pkg_id}/decision",
        json={"decision": "approve", "reason": "太原首选"},
    ).json()
    assert dec["status"] == "ok"
    assert dec["application_id"] is not None

    apps = client.get("/api/applications").json()["applications"]
    assert len(apps) == 1
    assert apps[0]["status"] == "待提交"

    upd = client.post(
        f"/api/applications/{apps[0]['id']}/status",
        json={"status": "已投递", "notes": "官网已提交"},
    ).json()
    assert upd["status"] == "已投递"

    exp = client.post("/api/export-queue").json()
    assert exp["count"] == 1
    assert exp["campus_count"] == 1
    assert exp["intern_count"] == 0
    assert Path(exp["md_path"]).is_file()
    assert Path(exp["campus_md_path"]).is_file()
    assert Path(exp["intern_md_path"]).is_file()

    db = Database(db_path)
    dig = build_daily_digest(db, output_dir=out_dir / "digest", min_score=80, top_n=10)
    assert dig["packages_count"] == 2
    assert dig["campus_packages_count"] == 1
    assert dig["intern_packages_count"] == 1
    assert "秋招 / 校招高分定制投递包" in dig["digest_markdown"]
    assert "实习高分定制投递包" in dig["digest_markdown"]
    assert Path(dig["digest_path"]).is_file()

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    email_res = send_qq_email_digest(load_user_config(), subject="test", body_text="body")
    assert email_res["status"] == "skipped_missing_smtp_env"


def test_render_daily_email_html_and_multipart_send(tmp_path: Path, monkeypatch) -> None:
    db_path, out_dir, _ = _seed_review_db(tmp_path)
    db = Database(db_path)
    dig = build_daily_digest(db, output_dir=out_dir / "digest", min_score=80, top_n=10)

    # Inject XSS test strings and verify safe HTML escaping + URL sanitization.
    dig["campus_packages"] = [
        {
            "score": 92,
            "decision": "pending",
            "company": "<script>alert(1)</script>晋商银行",
            "title": "财务管培生",
            "job_type": "校招",
            "cities": ["太原"],
            "source": "ncss",
            "factcheck_status": "passed",
            "url": "javascript:alert(1)",
        }
    ]
    html_doc = render_daily_email_html(
        digest=dig,
        reminders={
            "total_alerts": 1,
            "summary_text": "高分待审 1 项",
            "pending_high_score": [
                {"score": 92, "company": "晋商银行", "title": "财务管培生", "job_type": "校招"}
            ],
        },
        report={
            "funnel": {"active_jobs": 2, "total_jobs": 2, "rates": {"approval_rate_pct": 100.0}},
            "active_by_source": {"ncss": 1, "shixiseng": 1},
            "tuning_suggestions": ["保持每日扩源并及时在工作台勾选审核。"],
        },
    )
    assert "<!DOCTYPE html>" in html_doc
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_doc
    assert "javascript:alert(1)" not in html_doc
    assert "秋招 / 校招高分推荐" in html_doc
    assert "最新入库活跃岗位速览" in html_doc
    assert "东八区 16:00 推送" in html_doc

    captured: dict[str, object] = {}

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int = 20) -> None:
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, user: str, password: str) -> None:
            captured["user"] = user

        def send_message(self, msg) -> None:
            captured["content_type"] = msg.get_content_type()
            captured["parts"] = [part.get_content_type() for part in msg.iter_parts()]
            captured["to"] = msg["To"]

    monkeypatch.setenv("SMTP_HOST", "smtp.qq.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "sender@qq.com")
    monkeypatch.setenv("SMTP_PASS", "authcode")
    monkeypatch.setattr("job_agent.stage3.digest.smtplib.SMTP_SSL", _FakeSMTP)

    cfg = load_user_config()
    cfg.notifications.email_to = "target@qq.com"
    res = send_qq_email_digest(
        cfg,
        subject="HTML Digest",
        body_text="plain fallback",
        html_body=html_doc,
    )
    assert res["status"] == "sent"
    assert res["has_html"] is True
    assert captured["content_type"] == "multipart/alternative"
    assert captured["parts"] == ["text/plain", "text/html"]
    assert captured["to"] == "target@qq.com"

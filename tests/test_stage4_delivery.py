"""Tests for Stage 4 workflow classification, autofill extension export, and tracker."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from job_agent.cli import main as cli_main
from job_agent.config import UserConfig
from job_agent.db import Database
from job_agent.sources.base import is_restricted_university_portal
from job_agent.stage2.prefilter import evaluate_job_prefilter
from job_agent.stage3.review_server import create_review_app
from job_agent.stage4.delivery import (
    classify_delivery_workflow,
    cleanup_restricted_university_jobs,
    export_autofill_profile,
    parse_ncss_detail_html,
    prepare_delivery_bundles,
    summarize_delivery_tracker,
)


def test_classify_delivery_workflow_splits_direct_chat_and_portal() -> None:
    boss = classify_delivery_workflow(
        source="zhipin",
        url="https://www.zhipin.com/job_detail/abc.html",
        apply_channel="third_party",
        apply_target="https://www.zhipin.com/job_detail/abc.html",
    )
    assert boss["workflow"] == "direct_chat"
    assert boss["needs_autofill"] is False

    sxs = classify_delivery_workflow(
        source="shixiseng",
        url="https://www.shixiseng.com/intern/inn_123",
        apply_channel="third_party",
        apply_target="https://www.shixiseng.com/intern/inn_123",
    )
    assert sxs["workflow"] == "direct_chat"
    assert sxs["needs_autofill"] is False

    beisen = classify_delivery_workflow(
        source="givemeoc",
        url="https://demo.zhiye.com/campus/jobs",
        apply_channel="company_portal",
        apply_target="https://demo.zhiye.com/campus/jobs",
    )
    assert beisen["workflow"] == "portal_autofill"
    assert beisen["needs_autofill"] is True

    email_wf = classify_delivery_workflow(
        source="ncss",
        url="",
        apply_channel="email",
        apply_target="hr@example.com",
    )
    assert email_wf["workflow"] == "email"
    assert email_wf["needs_autofill"] is False


def test_export_autofill_profile_matches_extension_schema(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    profile_json = {
        "version_tag": "test-v1",
        "education": {
            "school": "示例财经学院",
            "college": "会计学院",
            "major": "会计学",
            "degree": "本科",
            "period": "2023.09 - 2027.06",
            "graduation_year": 2027,
            "core_courses": ["中级财务会计", "审计学"],
        },
        "certifications": ["初级会计职称"],
        "skills": [{"name": "Python", "level": "熟练"}],
        "experiences": [
            {
                "id": "exp_1",
                "category": "internship",
                "organization": "示范会计师事务所",
                "role": "审计实习生",
                "period": "2025.07 - 2025.09",
                "bullets": [{"id": "b1", "text": "参与凭证抽查与底稿整理。"}],
            },
            {
                "id": "exp_2",
                "category": "project",
                "organization": "数智财务ERP实训系统",
                "role": "核心开发与财务建模",
                "period": "2025.10 - 2026.01",
                "bullets": [{"id": "b2", "text": "完成凭证自动校验原型。"}],
            },
        ],
        "proper_nouns_whitelist": [],
    }
    qa_json = {
        "version_tag": "test-v1",
        "items": [
            {
                "id": "qa1",
                "question": "请做一个简短自我评价",
                "category": "自我介绍",
                "draft_answer": "具备财务专业基础与AI/Python实操经验。",
                "evidence_ids": ["b1"],
            }
        ],
    }
    secrets_json = {
        "full_name": "测试姓名",
        "phone": "13800001111",
        "email": "tester@example.com",
        "city_intent": "太原 / 济南",
        "demo_url": "http://example.invalid/demo",
        "political_status": "共青团员",
        "hometown": "山西太原",
    }
    (vault / "master_profile.json").write_text(json.dumps(profile_json), encoding="utf-8")
    (vault / "qa_bank.json").write_text(json.dumps(qa_json), encoding="utf-8")
    (vault / "personal_secrets.json").write_text(json.dumps(secrets_json), encoding="utf-8")

    out_backup = tmp_path / "autofill_extension_backup.json"
    out_raw = tmp_path / "autofill_profile_raw.json"
    cfg = UserConfig()
    summary = export_autofill_profile(
        cfg=cfg,
        output_path=out_backup,
        raw_output_path=out_raw,
        vault_dir=vault,
    )

    assert "13800001111" not in json.dumps(summary, ensure_ascii=False)
    assert out_backup.is_file() and out_raw.is_file()

    payload = json.loads(out_backup.read_text(encoding="utf-8"))
    assert payload["app"] == "resume-autofill-extension"
    profiles = payload["data"]["resumeProfiles"]
    assert len(profiles) == 2

    campus_data = profiles[0]["data"]
    expected_keys = {
        "basic",
        "education",
        "workExperience",
        "internship",
        "project",
        "training",
        "skills",
        "certificates",
        "languages",
        "family",
        "selfEvaluation",
        "jobIntent",
    }
    assert expected_keys.issubset(set(campus_data.keys()))
    assert campus_data["basic"]["name"] == "测试姓名"
    assert campus_data["basic"]["workYears"] == "应届生"
    assert campus_data["education"][0]["school"] == "示例财经学院"
    assert campus_data["education"][0]["startDate"] == "2023-09"
    assert campus_data["internship"][0]["company"] == "示范会计师事务所"
    assert campus_data["project"][0]["link"] == "http://example.invalid/demo"
    assert campus_data["selfEvaluation"] == "具备财务专业基础与AI/Python实操经验。"


def test_stage4_tracker_and_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "stage4.db"
    db = Database(db_path)
    db.init_schema()
    master_id = db.upsert_master_version(version_tag="v1", profile_json="{}", qa_bank_json="{}")

    db.upsert_jobs(
        [
            {
                "source": "zhipin",
                "source_job_id": "boss-1",
                "company": "晋商科技",
                "title": "财务实习生",
                "cities": ["太原"],
                "job_type": "实习",
                "jd_text": "协助日常账务",
                "url": "https://www.zhipin.com/job_detail/1.html",
                "apply_channel": "third_party",
                "apply_target": "https://www.zhipin.com/job_detail/1.html",
                "deadline": "",
                "industry": "软件",
                "status": "active",
                "dedup_hash": "h-boss-1",
                "priority_rank": 1,
            },
            {
                "source": "ncss",
                "source_job_id": "ncss-2",
                "company": "山能数智",
                "title": "财务管培生",
                "cities": ["济南"],
                "job_type": "校招",
                "jd_text": "官网网申",
                "url": "https://campus.example.com/beisen/apply",
                "apply_channel": "company_portal",
                "apply_target": "https://campus.example.com/beisen/apply",
                "deadline": "",
                "industry": "能源",
                "status": "active",
                "dedup_hash": "h-ncss-2",
                "priority_rank": 2,
            },
        ]
    )

    with db.connect() as conn:
        job_ids = [int(r[0]) for r in conn.execute("SELECT id FROM jobs ORDER BY id").fetchall()]

    for jid in job_ids:
        mid = db.insert_match(
            job_id=jid,
            master_version_id=master_id,
            rule_pass=True,
            score=88,
            reasons=[],
            gaps=[],
            strategy={},
            model="test",
            prompt_version="v1",
        )
        pkg_id = db.insert_package(
            job_id=jid,
            match_id=mid,
            master_version_id=master_id,
            resume_pdf_path="",
            diff_md_path="",
            qa={},
            greeting="您好，附带简历请查收。",
            retry_count=0,
            factcheck_status="pass",
        )
        db.record_decision(package_id=pkg_id, decision="approve")

    # Age first application as submitted 10 days ago
    now = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    old_ts = (now - timedelta(days=10)).isoformat()
    apps = db.list_applications()
    with db.connect() as conn:
        conn.execute(
            "UPDATE applications SET status = '已投递', submitted_at = ? WHERE id = ?",
            (old_ts, apps[0]["id"]),
        )

    summary = summarize_delivery_tracker(db, stale_days=7, now=now)
    assert summary["total"] == 2
    assert summary["by_workflow"]["direct_chat"] == 1
    assert summary["by_workflow"]["portal_autofill"] == 1
    assert summary["by_track"] == {"campus": 1, "intern": 1}
    assert summary["stale_count"] == 1

    app = create_review_app(db_path=db_path, output_root=tmp_path / "output")
    client = TestClient(app)
    r = client.get("/api/applications/summary?stale_days=7")
    assert r.status_code == 200
    assert r.json()["total"] == 2

    rc = cli_main(["--db", str(db_path), "track", "--stale-days", "7"])
    assert rc == 0


def test_prepare_delivery_bundles_and_ncss_enrichment(tmp_path: Path) -> None:
    sample_html = """
    <div class="jobdetail-box">
      <div class="mainContent mainContent-geshi">工作地点：山西省运城市盐湖区；网申入口：https://campus.demo.com/beisen/apply 或投递至 hr@demo-pharma.com</div>
    </div>
    <li>公司网址<span class="show">https://www.demo-pharma.com</span></li>
    """
    parsed = parse_ncss_detail_html(sample_html)
    assert "山西省运城市盐湖区" in parsed["detail_text"]
    assert parsed["company_site"] == "https://www.demo-pharma.com"
    assert parsed["emails"] == ["hr@demo-pharma.com"]
    assert parsed["external_urls"] == ["https://campus.demo.com/beisen/apply"]

    db_path = tmp_path / "prep.db"
    db = Database(db_path)
    db.init_schema()
    master_id = db.upsert_master_version(version_tag="v1", profile_json="{}", qa_bank_json="{}")
    db.upsert_jobs(
        [
            {
                "source": "ncss",
                "source_job_id": "ncss-demo-1",
                "company": "示范医药山西公司",
                "title": "会计助理",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "【面向专业】会计学",
                "url": "https://www.ncss.cn/student/jobs/ncss-demo-1/detail.html",
                "apply_channel": "third_party",
                "apply_target": "https://www.ncss.cn/student/jobs/ncss-demo-1/detail.html",
                "deadline": "",
                "industry": "医药",
                "status": "active",
                "dedup_hash": "h-ncss-demo-1",
                "priority_rank": 1,
            }
        ]
    )
    with db.connect() as conn:
        jid = int(conn.execute("SELECT id FROM jobs").fetchone()[0])

    pdf_src = tmp_path / "packages" / "demo" / "resume.pdf"
    pdf_src.parent.mkdir(parents=True, exist_ok=True)
    pdf_src.write_bytes(b"%PDF-1.4\n%stage4\n")

    mid = db.insert_match(
        job_id=jid,
        master_version_id=master_id,
        rule_pass=True,
        score=90,
        reasons=[],
        gaps=[],
        strategy={},
        model="test",
        prompt_version="v1",
    )
    pkg_id = db.insert_package(
        job_id=jid,
        match_id=mid,
        master_version_id=master_id,
        resume_pdf_path=str(pdf_src),
        diff_md_path="",
        qa={"请用 200-300 字做一下自我介绍": "具备会计学与ERP实操经验。"},
        greeting="您好，附带简历请查收。",
        retry_count=0,
        factcheck_status="pass",
    )
    dec = db.record_decision(package_id=pkg_id, decision="approve")
    app_id = int(dec["application_id"])

    db.update_application_status(application_id=app_id, status="待提交", notes="保留这条备注")
    db.update_application_status(application_id=app_id, status="已投递", notes=None)
    assert db.list_applications()[0]["notes"] == "保留这条备注"

    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=sample_html))
    out_root = tmp_path / "output"
    with httpx.Client(transport=transport) as mock_client:
        res = prepare_delivery_bundles(db, output_root=out_root, enrich_ncss=True, client=mock_client)

    assert res["prepared_count"] == 1
    assert res["enriched_count"] == 1
    staged_pdf = out_root / "ready_to_submit" / "秋招" / "示范医药山西公司.pdf"
    assert staged_pdf.is_file()
    checklist = Path(res["checklist_path"]).read_text(encoding="utf-8")
    assert "示范医药山西公司" in checklist
    assert "山西省运城市盐湖区" in checklist
    assert "具备会计学与ERP实操经验" in checklist

    # Run Workbench API check with enrich=false
    app = create_review_app(db_path=db_path, output_root=out_root)
    client = TestClient(app)
    r = client.post("/api/prepare-delivery?enrich=false")
    assert r.status_code == 200
    assert r.json()["prepared_count"] == 1


def test_restricted_university_portal_excluded_end_to_end(tmp_path: Path) -> None:
    restricted_flag, reason = is_restricted_university_portal(
        source="ncss",
        url="https://www.ncss.cn/student/jobs/X1/detail.html",
        jd_text="【来源高校/站点】中南大学\n【面向专业】会计学",
    )
    assert restricted_flag is True
    assert "中南大学" in reason

    open_flag, _ = is_restricted_university_portal(
        source="ncss",
        url="https://www.ncss.cn/student/jobs/X2/detail.html",
        jd_text="【来源高校/站点】智联招聘",
    )
    assert open_flag is False

    own_flag, _ = is_restricted_university_portal(
        source="ncss",
        url="https://www.ncss.cn/student/jobs/X3/detail.html",
        jd_text="【来源高校/站点】示范大学",
        allowed_schools=("示范大学",),
    )
    assert own_flag is False

    email_upgraded, _ = is_restricted_university_portal(
        source="ncss",
        url="https://example-corp.com/jobs/195538/index.html",
        jd_text="【来源高校/站点】中南大学",
        apply_channel="email",
        apply_target="hr@example-corp.com",
    )
    assert email_upgraded is False

    cfg = UserConfig()
    outcome = evaluate_job_prefilter(
        {
            "title": "财务管理岗",
            "company": "中铁三局集团有限公司",
            "cities": ["太原"],
            "job_type": "校招",
            "source": "ncss",
            "url": "https://www.ncss.cn/student/jobs/X1/detail.html",
            "jd_text": "【来源高校/站点】中南大学\n会计学财务管理",
        },
        cfg,
    )
    assert outcome.rule_pass is False
    assert outcome.city_tier == "restricted_portal"
    assert outcome.reject_reason.startswith("restricted_university_portal:")

    wf = classify_delivery_workflow(
        source="ncss",
        url="https://www.ncss.cn/student/jobs/X1/detail.html",
        jd_text="【来源高校/站点】中南大学",
    )
    assert wf["workflow"] == "restricted_campus"
    assert wf["needs_autofill"] is False

    db = Database(tmp_path / "restricted.db")
    db.init_schema()
    master_id = db.upsert_master_version(version_tag="v1", profile_json="{}", qa_bank_json="{}")
    db.upsert_jobs(
        [
            {
                "source_job_id": "csu-pending",
                "source": "ncss",
                "company": "外校认证受限企业",
                "title": "财务专员",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "【来源高校/站点】中南大学",
                "url": "https://www.ncss.cn/student/jobs/X1/detail.html",
                "apply_channel": "third_party",
                "apply_target": "https://www.ncss.cn/student/jobs/X1/detail.html",
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": "h-csu-pending",
                "priority_rank": 1,
            },
            {
                "source_job_id": "ztsj-upgraded",
                "source": "ncss",
                "company": "中铁三局集团有限公司",
                "title": "财务管理岗",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "【来源高校/站点】中南大学",
                "url": "https://example-corp.com/jobs/195538/index.html",
                "apply_channel": "email",
                "apply_target": "hr@example-corp.com",
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": "h-ztsj-upgraded",
                "priority_rank": 1,
            },
            {
                "source_job_id": "open-zhaopin-1",
                "source": "zhaopin",
                "company": "国药集团山西医疗器械有限公司",
                "title": "会计（校招）",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "正常智联公开直投岗位",
                "url": "https://www.zhaopin.com/jobdetail/OPEN1.htm",
                "apply_channel": "third_party",
                "apply_target": "https://www.zhaopin.com/jobdetail/OPEN1.htm",
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": "h-open-zp",
                "priority_rank": 1,
            },
            {
                "source_job_id": "open-ncss-zp",
                "source": "ncss",
                "company": "公开来源企业",
                "title": "财务专员",
                "cities": ["太原"],
                "job_type": "校招",
                "jd_text": "【来源高校/站点】智联招聘",
                "url": "https://www.ncss.cn/student/jobs/OPENNCSS/detail.html",
                "apply_channel": "third_party",
                "apply_target": "https://www.ncss.cn/student/jobs/OPENNCSS/detail.html",
                "deadline": "",
                "industry": "",
                "status": "active",
                "dedup_hash": "h-open-ncss",
                "priority_rank": 1,
            },
        ]
    )
    with db.connect() as conn:
        pending_jid = int(
            conn.execute("SELECT id FROM jobs WHERE source_job_id='csu-pending'").fetchone()[0]
        )

    mid = db.insert_match(
        job_id=pending_jid,
        master_version_id=master_id,
        rule_pass=True,
        score=85,
        reasons=[],
        gaps=[],
        strategy={},
        model="test",
        prompt_version="v1",
    )
    db.insert_package(
        job_id=pending_jid,
        match_id=mid,
        master_version_id=master_id,
        resume_pdf_path="",
        diff_md_path="",
        qa={},
        greeting="",
        retry_count=0,
        factcheck_status="pass",
    )

    assert len(db.list_packages_for_review()) == 1
    res = cleanup_restricted_university_jobs(db)
    assert res["scanned"] == 4
    assert res["marked_restricted"] == 1
    assert res["remaining_active"] == 3
    # Pending restricted package is automatically hidden from the review queue.
    assert db.list_packages_for_review() == []

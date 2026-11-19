"""Tests for Stage 2: prefilter, anti-hallucination factcheck, matcher, tailor retry, and 1-page PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from job_agent.config import UserConfig
from job_agent.db import Database
from job_agent.master import (
    MasterBullet,
    MasterEducation,
    MasterExperience,
    MasterProfile,
    QABank,
    QABankItem,
    SkillItem,
)
from job_agent.sources.base import compute_dedup_hash
from job_agent.stage2.factcheck import verify_tailored_resume
from job_agent.stage2.matcher import run_match_batch
from job_agent.stage2.pdf_render import (
    load_safe_display_contact,
    render_resume_html,
    render_single_page_resume_pdf,
    should_include_demo_url,
)
from job_agent.stage2.prefilter import evaluate_job_prefilter
from job_agent.stage2.tailor import build_package_for_match


def _sample_profile() -> MasterProfile:
    return MasterProfile(
        version_tag="v1.0",
        education=MasterEducation(
            school="山西财经大学",
            college="会计学院",
            major="会计学",
            degree="本科",
            period="2023.09-2027.06",
            graduation_year=2027,
            core_courses=["中级财务会计", "财务管理", "审计学"],
        ),
        certifications=["初级会计职称", "C1驾驶证"],
        skills=[
            SkillItem(name="用友U8", level="熟练", category="ERP"),
            SkillItem(name="Python", level="熟练", category="技术"),
        ],
        experiences=[
            MasterExperience(
                id="exp_1",
                category="project",
                organization="4家上市企业财务分析",
                role="分析员",
                period="2025.03-2025.06",
                bullets=[
                    MasterBullet(
                        id="b_fin_1",
                        text="独立编写4家企业财务分析材料（数据由同事提供），运用Python提取年报指标",
                        tags=["财务分析", "Python"],
                        facts=["4家", "独立"],
                    )
                ],
            ),
            MasterExperience(
                id="exp_2",
                category="training",
                organization="校内ERP沙盘实训",
                role="财务核算组",
                period="2025.09-2025.11",
                bullets=[
                    MasterBullet(
                        id="b_erp_1",
                        text="参与用友U8总账建账、凭证录入与成本核算实训，按期完成100%模拟账套结转",
                        tags=["ERP", "用友U8", "总账"],
                        facts=["100%"],
                    )
                ],
            ),
        ],
        proper_nouns_whitelist=["用友U8", "Python", "Excel", "初级会计职称", "C1驾驶证"],
    )


def test_prefilter_ranks_shanxi_finance_and_rejects_sales_or_wrong_city() -> None:
    cfg = UserConfig()
    cfg.preferences.primary_cities = ["太原", "山西"]
    cfg.preferences.secondary_cities = ["济南", "青岛", "西安"]

    good = evaluate_job_prefilter(
        {"company": "中铁三局", "title": "财务管理岗", "cities": ["太原"], "job_type": "校招"},
        cfg,
    )
    assert good.rule_pass is True
    assert good.city_tier == "primary"

    sec = evaluate_job_prefilter(
        {"company": "海信集团", "title": "财务管培生", "cities": ["青岛"], "job_type": "校招"},
        cfg,
    )
    assert sec.rule_pass is True
    assert sec.city_tier == "secondary"
    assert good.rule_score_hint > sec.rule_score_hint

    sales = evaluate_job_prefilter(
        {"company": "牧原", "title": "生鲜销售管培生", "cities": ["太原"], "job_type": "校招"},
        cfg,
    )
    assert sales.rule_pass is False

    wrong_city = evaluate_job_prefilter(
        {"company": "深圳某司", "title": "财务专员", "cities": ["深圳"], "job_type": "校招"},
        cfg,
    )
    assert wrong_city.rule_pass is False

    # Expanded target directions: AI / Data Analysis / HR / Ops / Finance / ERP Implementation
    for extra_title in (
        "AI产品运营助理",
        "数据分析师（2027届）",
        "人力资源专员",
        "金融风控管培生",
        "ERP实施顾问",
    ):
        extra = evaluate_job_prefilter(
            {"company": "山西数智企业", "title": extra_title, "cities": ["太原"], "job_type": "校招"},
            cfg,
        )
        assert extra.rule_pass is True, extra_title

    hard_eng = evaluate_job_prefilter(
        {"company": "某芯片司", "title": "C++嵌入式软件工程师", "cities": ["太原"], "job_type": "校招"},
        cfg,
    )
    assert hard_eng.rule_pass is False


def test_factcheck_blocks_hallucinated_numbers_tools_exaggerations_and_english() -> None:
    profile = _sample_profile()

    # Valid pass: keeps original allowed "独立" (in facts) & 4家 / 100% / Python / 用友U8
    ok = verify_tailored_resume(
        {
            "summary": "2027届会计学本科，熟悉用友U8与Python财务分析。",
            "selected": [
                {"id": "b_fin_1", "rewritten": "独立编写4家企业财务分析材料并运用Python处理年报指标"},
                {"id": "b_erp_1", "rewritten": "参与用友U8总账建账与成本核算实训，完成100%模拟账套结转"},
            ],
        },
        profile,
        job_type="校招",
    )
    assert ok.passed is True

    # Violation 1: fake bullet id + fake SAP + fake number 30% + forbidden "主导" + CET-4 fabrication + intern timing in campus role
    bad = verify_tailored_resume(
        {
            "summary": "通过大学英语四级，最快下周到岗，熟悉SAP系统。",
            "selected": [
                {"id": "b_fake_id", "rewritten": "测试"},
                {"id": "b_erp_1", "rewritten": "主导企业实习中的ERP项目，效率提升30%"},
            ],
        },
        profile,
        job_type="校招",
    )
    assert bad.passed is False
    joined = bad.as_feedback()
    assert "b_fake_id" in joined
    assert "SAP" in joined
    assert "30%" in joined
    assert "主导" in joined
    assert "通过大学英语四级" in joined
    assert "实习" in joined


class _FakeStage2LLM:
    def __init__(self) -> None:
        self.tailor_calls = 0

    def generate_json(self, *, asset, payload, model_override=None) -> dict[str, Any]:
        if asset.task == "job_match":
            return {
                "score": 88,
                "hard_filter_pass": True,
                "reasons": [
                    {
                        "dimension": "专业对口",
                        "jd_quote": "会计学本科",
                        "evidence": "会计学",
                        "impact": "positive",
                    }
                ],
                "gaps": [],
                "strategy": {
                    "focus_tags": ["财务分析", "用友U8"],
                    "avoid_angles": [],
                    "tailor_notes": "突出ERP实训",
                },
            }
        # First tailor call returns hallucinated number 50% -> triggers retry -> second call succeeds!
        self.tailor_calls += 1
        if self.tailor_calls == 1:
            return {
                "summary": "2027届会计学本科。",
                "selected": [
                    {"id": "b_fin_1", "rewritten": "独立完成4家企业财务分析，效率提升50%"}
                ],
            }
        return {
            "summary": "2027届会计学本科，熟悉用友U8与Python财务分析。",
            "selected": [
                {"id": "b_fin_1", "rewritten": "独立编写4家企业财务分析材料并运用Python整理年报"},
                {"id": "b_erp_1", "rewritten": "参与用友U8总账建账、凭证录入与模拟账套100%结转"},
            ],
        }


def test_stage2_end_to_end_match_retry_and_single_page_pdf(tmp_path: Path) -> None:
    db = Database(tmp_path / "stage2.db")
    db.init_schema()
    profile = _sample_profile()
    qa_bank = QABank(
        version_tag="v1.0",
        items=[
            QABankItem(
                id="qa_1",
                question="为什么选择财务岗位？",
                category="motivation",
                draft_answer="结合会计学专业与用友U8实训经验，希望深耕企业财务管理。",
                evidence_ids=["b_erp_1"],
            )
        ],
    )
    master_id = db.upsert_master_version(
        version_tag="v1.0",
        profile_json=profile.model_dump_json(),
        qa_bank_json=qa_bank.model_dump_json(),
    )
    job = {
        "source": "ncss",
        "source_job_id": "N99",
        "company": "中铁三局",
        "title": "财务管理岗（ERP信息化方向）",
        "cities": ["太原"],
        "job_type": "校招",
        "jd_text": "面向会计学本科，熟悉用友U8等ERP软件。",
        "url": "https://www.ncss.cn/student/jobs/N99/detail.html",
        "apply_channel": "third_party",
        "apply_target": "https://www.ncss.cn/student/jobs/N99/detail.html",
        "dedup_hash": compute_dedup_hash(company="中铁三局", title="财务管理岗", job_type="校招"),
        "priority_rank": 10,
    }
    db.upsert_jobs([job])
    with db.connect() as conn:
        job_row = dict(conn.execute("SELECT * FROM jobs LIMIT 1").fetchone())

    cfg = UserConfig()
    cfg.preferences.primary_cities = ["太原", "山西"]
    cfg.profile.english_status.cet4_best_score = 405
    cfg.profile.english_status.gaokao_english = "高考英语良好"

    prompts_root = Path(__file__).resolve().parents[1] / "prompts"
    llm = _FakeStage2LLM()
    match_stats = run_match_batch(
        db=db,
        cfg=cfg,
        llm=llm,
        prompts_root=prompts_root,
        candidates=[job_row],
        master_version_id=master_id,
        profile=profile,
    )
    assert match_stats["scored"] == 1
    assert match_stats["high_score_matches"] == 1

    pairs = db.get_matches_needing_packages(master_version_id=master_id, min_score=80, limit=5)
    assert len(pairs) == 1
    pkg_job, match_row = pairs[0]

    assert should_include_demo_url(pkg_job) is True
    res = build_package_for_match(
        db=db,
        cfg=cfg,
        llm=llm,
        prompts_root=prompts_root,
        output_root=tmp_path / "output",
        job=pkg_job,
        match_row=match_row,
        master_version_id=master_id,
        profile=profile,
        qa_bank=qa_bank,
    )
    assert res["factcheck_status"] == "pass"
    assert res["retry_count"] == 1  # Retried after rejecting 50%
    assert res["page_count"] == 1

    pdf_path = Path(res["pdf_path"])
    assert pdf_path.exists()
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 1
    extracted = reader.pages[0].extract_text() or ""
    assert "会计学" in extracted
    assert "用友" in extracted


def test_render_pdf_helper_direct(tmp_path: Path) -> None:
    profile = _sample_profile()
    out_pdf = tmp_path / "direct.pdf"
    meta = render_single_page_resume_pdf(
        profile=profile,
        tailored={
            "summary": "2027届会计学本科。",
            "selected": [{"id": "b_fin_1", "rewritten": "独立编写4家企业财务分析材料"}],
        },
        job={"company": "晋能控股", "title": "财务岗", "job_type": "校招", "jd_text": "基础财务"},
        output_pdf_path=out_pdf,
    )
    assert meta["page_count"] == 1
    assert meta["extracted_text_chars"] > 30


def test_render_pdf_with_avatar_photo(tmp_path: Path) -> None:
    profile = _sample_profile()
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    # Minimal 1x1 PNG bytes
    png_1x1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc````\x00\x00"
        b"\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (vault_dir / "avatar.png").write_bytes(png_1x1)
    contact = load_safe_display_contact(vault_dir)
    assert contact["avatar_data_uri"].startswith("data:image/png;base64,")

    html_out = render_resume_html(
        profile=profile,
        tailored={"summary": "测试摘要", "selected": [{"id": "b_fin_1", "rewritten": "独立编写4家企业材料"}]},
        job={"company": "晋能控股", "title": "财务岗", "job_type": "校招", "jd_text": "基础财务"},
        contact=contact,
    )
    assert '<div class="photo-frame"><img src="data:image/png;base64,' in html_out
    assert '<div class="top-stripe"></div>' in html_out
    assert "job-intent-badge" in html_out
    assert "skills-box" in html_out
    assert "个人定位" not in html_out

    out_pdf = tmp_path / "with_photo.pdf"
    meta = render_single_page_resume_pdf(
        profile=profile,
        tailored={"summary": "测试摘要", "selected": [{"id": "b_fin_1", "rewritten": "独立编写4家企业材料"}]},
        job={"company": "晋能控股", "title": "财务岗", "job_type": "校招", "jd_text": "基础财务"},
        output_pdf_path=out_pdf,
        contact=contact,
    )
    assert meta["page_count"] == 1

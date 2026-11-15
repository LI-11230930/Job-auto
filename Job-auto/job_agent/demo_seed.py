"""Built-in sanitized guest demo dataset seeder (zero API key required)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .db import Database


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for cand in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if Path(cand).is_file():
            try:
                return ImageFont.truetype(cand, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _render_demo_pdf(
    pdf_path: Path,
    *,
    company: str,
    job_title: str,
    track: str,
    score: int,
    highlights: list[str],
) -> None:
    """Render a crisp single-page A4 sample resume PDF cleanly via Pillow (no browser overhead)."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1240, 1754  # 150 DPI A4
    img = Image.new("RGB", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Top Arc/Purple-accent stripe aligned with Scheme I
    draw.rectangle([0, 0, w, 18], fill="#7C3AED")
    draw.rectangle([0, 18, w, 24], fill="#2E1065")

    f_h1 = _load_font(42)
    f_sec = _load_font(24)
    f_body = _load_font(20)
    f_small = _load_font(17)

    y = 66
    draw.text((78, y), "林子轩（示例简历档案）", fill="#1E1B4B", font=f_h1)
    draw.rounded_rectangle([820, y + 6, 1162, y + 52], radius=10, fill="#EDE9FE", outline="#7C3AED", width=2)
    draw.text((838, y + 14), f"定制目标：{track} · 匹配 {score}", fill="#6D28D9", font=f_small)
    y += 66
    draw.text(
        (78, y),
        f"求职意向：{company} - {job_title}   |   demo@example.com   |   杭州 / 上海",
        fill="#4B5563",
        font=f_small,
    )
    y += 46
    draw.line([(78, y), (1162, y)], fill="#E9D5FF", width=3)

    def _wrap_line(text: str, font_obj: Any, max_width: int = 1040) -> list[str]:
        out: list[str] = []
        buf = ""
        for ch in text:
            cand = buf + ch
            if draw.textlength(cand, font=font_obj) > max_width and buf:
                out.append(buf)
                buf = ch
            else:
                buf = cand
        if buf:
            out.append(buf)
        return out

    def section(title: str, lines: list[str], cur_y: int) -> int:
        cur_y += 26
        draw.rectangle([78, cur_y + 4, 86, cur_y + 30], fill="#7C3AED")
        draw.text((98, cur_y), title, fill="#2E1065", font=f_sec)
        cur_y += 42
        for ln in lines:
            wrapped = _wrap_line(f"• {ln}", f_body, max_width=1050)
            for idx, part in enumerate(wrapped):
                x_pos = 92 if idx == 0 else 110
                draw.text((x_pos, cur_y), part, fill="#1F2937", font=f_body)
                cur_y += 30
            cur_y += 4
        return cur_y

    y = section(
        "教育背景  Education",
        [
            "示范财经大学  |  会计学（本科 · 2027届）  |  主修财务会计、审计学、税务实务、管理会计",
            "英语能力：CET-4 已通过（实事核验基线示例：严格按原档案标注，不虚构未取得证书）",
            "专业技能：Excel 高级透视表与 VBA 自动化、用友 U8 / 金蝶云财务核算、Python 数据清洗",
        ],
        y,
    )
    y = section("针对该岗位的 AI 重排要点  Tailored Highlights", highlights, y)
    y = section(
        "实习与实训经历  Selected Experience",
        [
            "某会计师事务所审计实训组（助理）：独立核对 120+ 张银行对账单与往来科目函证，准确率 99.4%。",
            "校级企业财税沙盘竞赛（财务总监角色）：搭建多期现金流预测模型，获得省级二等奖。",
            "本地校园财务数据分析实践：利用 Python Pandas 自动比对月度费用异常，统计耗时缩短 70%。",
        ],
        y,
    )
    y = section(
        "网申自检说明  Local-First Fact Check",
        [
            "本 PDF 由内置示例演示模块在本地生成（零第三方统计，所有事实条目 100% 源自示例主档案）。",
            "点击右侧「通过并加入投递队列」后，可在投递追踪看板中切换列表 / 四列看板查看完整流转。",
        ],
        y,
    )

    draw.text((78, h - 64), "Job-auto 独立桌面求职助手 · 方案 I（星夜紫藤 × 霜白）示例演示页", fill="#9CA3AF", font=f_small)
    img.save(str(pdf_path), "PDF", resolution=150.0)


def seed_demo_workspace(db: Database, *, output_root: Path) -> dict[str, Any]:
    """Populate clean sample master profile, 3 curated jobs, PDFs, and welcome notifications."""
    db.init_schema()
    existing = db.list_packages_for_review(
        decision_filter="all",
        job_type_filter="all",
        min_score=0,
        limit=50,
    )
    if any(str(p.get("source") or "") == "demo_sample" for p in existing):
        return {
            "status": "already_seeded",
            "packages_count": len(existing),
            "message": "工作区已包含示例体验数据，无需重复载入。",
        }

    master_profile = {
        "name": "林子轩（示例档案）",
        "education": {
            "school": "示范财经大学",
            "degree": "本科",
            "major": "会计学",
            "period": "2023-09 ~ 2027-06",
            "courses": ["财务会计", "审计学", "管理会计", "Python 数据分析"],
        },
        "experiences": [
            {
                "org": "示范会计师事务所审计实训",
                "role": "审计实习助理",
                "bullets": [
                    {"bullet_id": "demo-b1", "text": "参与企业年度财务报表审计底稿编制与银行存款余额调节表核对，发现并修正 4 处跨期凭证误差"},
                    {"bullet_id": "demo-b2", "text": "使用 Excel 数据透视表及 VLOOKUP 对 3,000+ 笔应收账款进行账龄分层，效率提升 60%"},
                ],
            },
            {
                "org": "Python 财务数据分析实践",
                "role": "数据分析负责人",
                "bullets": [
                    {"bullet_id": "demo-b3", "text": "基于 Pandas 搭建月度费用预算偏差自动预警脚本，将人工复核时长从 3 小时压缩至 20 分钟"},
                    {"bullet_id": "demo-b4", "text": "使用用友 U8 与金蝶云完成多维度凭证录入与期末结账模拟实训"},
                ],
            },
        ],
    }
    qa_bank = {
        "英语说明": "CET-4 已通过，CET-6 备考中（按实事核验规范标注）",
        "到岗时间": "一周内到岗，可连续实习 3–6 个月",
        "核心优势": "具备扎实的审计底稿实操经验与 Python 财务数据处理自动化能力",
    }
    master_id = db.upsert_master_version(
        version_tag="v1.0-demo",
        profile_json=json.dumps(master_profile, ensure_ascii=False),
        qa_bank_json=json.dumps(qa_bank, ensure_ascii=False),
    )

    demo_jobs = [
        {
            "source": "demo_sample",
            "source_job_id": "demo-001",
            "company": "晋商银行（示例企业）",
            "title": "总行财务会计管培生（2027届校招）",
            "cities": ["杭州", "上海"],
            "job_type": "校招",
            "jd_text": "【示例岗位】负责财务报表编制、银企对账及预算分析管理，要求会计/财务管理本科 2027 届毕业生，熟悉 Excel 与 ERP 财务软件。",
            "url": "https://example.com/demo/bank-finance",
            "apply_channel": "company_portal",
            "apply_target": "https://example.com/demo/bank-finance",
            "deadline": "2026-11-28",
            "industry": "金融/银行",
            "status": "active",
            "dedup_hash": "demo-hash-001",
            "priority_rank": 1,
            "score": 94,
            "reasons": [
                {"dimension": "专业匹配", "score": 29, "evidence": "会计学本科（2027届）完全契合"},
                {"dimension": "城市匹配", "score": 25, "evidence": "首选城市杭州直达"},
                {"dimension": "经历匹配", "score": 15, "evidence": "银企对账与财务数据分析经历高度吻合"},
            ],
            "gaps": ["尚未取得 CET-6 证书，网申备注按真实档案填写，禁止虚构"],
            "highlights": [
                "【匹配强项】具备银企余额调节表核对及 3,000+ 笔往来账龄分析实操经验",
                "【效率增益】掌握用友 U8/金蝶云与 Excel/Python 自动化对账脚本，上手快",
                "【事实约束】如实标明杭州/上海意向与英语现状，零虚构指标",
            ],
            "greeting": "您好！我是示范财经大学 2027 届会计学本科生，具备银企对账与财务数据分析实践经验，非常希望申请贵行财务会计管培生岗位。",
        },
        {
            "source": "demo_sample",
            "source_job_id": "demo-002",
            "company": "立信审计团队（示例所）",
            "title": "年报审计助理（校招直通）",
            "cities": ["济南", "青岛"],
            "job_type": "校招",
            "jd_text": "【示例岗位】协助注册会计师完成货币资金、应收账款函证及年报底稿归档工作，工作细致认真，熟练使用 Excel。",
            "url": "https://example.com/demo/audit-assistant",
            "apply_channel": "email",
            "apply_target": "hr-demo@example.com",
            "deadline": "2026-12-05",
            "industry": "会计师事务所",
            "status": "active",
            "dedup_hash": "demo-hash-002",
            "priority_rank": 2,
            "score": 91,
            "reasons": [
                {"dimension": "经历匹配", "score": 15, "evidence": "具备完整审计底稿与应收函证练习"},
                {"dimension": "城市匹配", "score": 22, "evidence": "济南/青岛目标区域覆盖"},
            ],
            "gaps": [],
            "highlights": [
                "【审计底稿经验】曾参与货币资金与往来科目函证抽凭，熟悉工作底稿规范",
                "【数据处理力】能用 Excel 透视表高效清洗大批量明细账，降低差错率",
                "【抗压与稳定性】目标聚焦财审一线，支持出差盘点与年报高峰节奏",
            ],
            "greeting": "您好，看到贵团队正在招聘审计助理，我有审计底稿编制与函证核对实训经验，已随信附上一页式定制简历请查阅。",
        },
        {
            "source": "demo_sample",
            "source_job_id": "demo-003",
            "company": "数智财务科技（示例）",
            "title": "财务数据分析实习生（可转正）",
            "cities": ["西安", "成都"],
            "job_type": "实习",
            "jd_text": "【示例岗位】协助完成财务月度经营报表自动化、异常费用监控及 Python/SQL 数据清洗，每周出勤 4 天以上。",
            "url": "https://example.com/demo/fin-data-intern",
            "apply_channel": "third_party",
            "apply_target": "https://example.com/demo/fin-data-intern",
            "deadline": "2026-11-22",
            "industry": "软件/ERP",
            "status": "active",
            "dedup_hash": "demo-hash-003",
            "priority_rank": 1,
            "score": 88,
            "reasons": [
                {"dimension": "技能匹配", "score": 15, "evidence": "Python Pandas 月报脚本与财务背景双匹配"},
                {"dimension": "成长空间", "score": 18, "evidence": "实习可转正，技术+财务复合赛道"},
            ],
            "gaps": ["注意确认学期课程与每周 4 天到岗时间协调"],
            "highlights": [
                "【复合背景】会计学专业 + Python Pandas 自动化脚本实战，能直接接手月报清洗",
                "【可量化成果】曾将月度异常费用统计耗时从 3 小时压至 20 分钟",
                "【即刻衔接】熟悉 ERP 数据结构，一周内即可投入实习支持",
            ],
            "greeting": "您好！我具备会计专业背景及 Python 财务报表自动化实战经验，一周内可到岗支持贵司财务数据分析实习。",
        },
    ]

    db.upsert_jobs(demo_jobs)
    created_pkgs = 0
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, company, title, job_type FROM jobs WHERE source = 'demo_sample' ORDER BY id ASC"
        ).fetchall()
    row_by_company = {str(r["company"]): r for r in rows}

    for item in demo_jobs:
        r = row_by_company.get(item["company"])
        if not r:
            continue
        job_id = int(r["id"])
        match_id = db.insert_match(
            job_id=job_id,
            master_version_id=master_id,
            rule_pass=True,
            score=item["score"],
            reasons=item["reasons"],
            gaps=item["gaps"],
            strategy={"focus_tags": [item["industry"]]},
            model="demo-sandbox",
            prompt_version="demo-v1",
        )
        pkg_dir = output_root / "packages" / f"demo_{job_id}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pkg_dir / "resume.pdf"
        diff_path = pkg_dir / "diff.md"
        _render_demo_pdf(
            pdf_path,
            company=item["company"],
            job_title=item["title"],
            track=item["job_type"],
            score=item["score"],
            highlights=item["highlights"],
        )
        diff_path.write_text(
            "# 定制简历微调说明（示例模式）\n\n"
            f"- 目标企业：{item['company']}\n"
            f"- 目标岗位：{item['title']}\n"
            "- 事实核验结果：pass（全部要点命中示范主档案 `v1.0-demo`）\n"
            "- 重点前置经历：\n" + "\n".join(f"  - {h}" for h in item["highlights"]),
            encoding="utf-8",
        )
        db.insert_package(
            job_id=job_id,
            match_id=match_id,
            master_version_id=master_id,
            resume_pdf_path=str(pdf_path),
            diff_md_path=str(diff_path),
            qa={
                "英语水平说明": qa_bank["英语说明"],
                "最快到岗时间": qa_bank["到岗时间"],
                "为何适合该岗位": item["highlights"][0],
            },
            greeting=item["greeting"],
            retry_count=0,
            factcheck_status="pass",
        )
        created_pkgs += 1

    db.add_notification(
        title="示例模式已就绪：新增 3 个高匹配示范岗位",
        body="无需提前配置任何 API Key，现在即可在左侧挑选岗位、审阅右侧定制 PDF、体验通过加入看板和 Ctrl+K 快捷命令。",
        category="system",
        level="info",
        action_tab="detail",
    )
    db.add_notification(
        title="隐私保护提示：100% 本地优先，零第三方统计",
        body="当前所有示例简历、PDF 与投递队列只存放在您本机 local/data 目录中；云端加密中转保持解耦预留接口。",
        category="privacy",
        level="info",
        action_tab="settings",
    )

    return {
        "status": "ok",
        "packages_created": created_pkgs,
        "master_version": "v1.0-demo",
        "message": f"已载入 {created_pkgs} 份完整示范岗位与定制单页简历 PDF，立即开始体验！",
    }

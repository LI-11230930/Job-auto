"""Local project progress data tracker and standalone HTML dashboard generator."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_project_root, load_user_config
from .db import Database

FINANCE_KEYWORDS = (
    "财务",
    "会计",
    "审计",
    "资金",
    "税务",
    "预算",
    "erp",
    "成本",
    "管培",
    "实施",
    "管理",
    "人力",
    "运营",
    "数据分析",
    "商业分析",
    "金融",
    "风控",
    "ai",
    "人工智能",
    "大模型",
    "数智",
)


def _source_bucket(source_name: str) -> str:
    s = (source_name or "").lower()
    if s.startswith("campus_site:"):
        return "campus_site"
    if s in {"ncss", "zhaopin", "shixiseng", "zhipin", "51job", "iguopin"}:
        return s
    return "manual"


def collect_live_db_metrics(
    db_path: Path,
    *,
    primary_cities: list[str],
    secondary_cities: list[str],
) -> dict[str, Any]:
    """Read real-time aggregate metrics from SQLite without touching non-db secrets."""
    empty = {
        "db_exists": False,
        "total_jobs": 0,
        "by_job_type": {},
        "by_source_bucket": {},
        "by_source_raw": {},
        "primary_city_jobs": 0,
        "primary_finance_jobs": 0,
        "secondary_city_jobs": 0,
        "secondary_finance_jobs": 0,
        "latest_master_version": None,
        "master_bullet_count": 0,
        "qa_count": 0,
        "recent_runs": [],
    }
    if not db_path.exists():
        return empty

    db = Database(db_path)
    with db.connect() as conn:
        try:
            rows = conn.execute(
                "SELECT source, job_type, cities_json, company, title FROM jobs"
            ).fetchall()
        except sqlite3.OperationalError:
            return empty

        by_job_type: dict[str, int] = {}
        by_source_bucket: dict[str, int] = {}
        by_source_raw: dict[str, int] = {}
        primary_hits = 0
        primary_fin_hits = 0
        secondary_hits = 0
        secondary_fin_hits = 0

        primary_tokens = {c.strip() for c in primary_cities if c.strip()}
        secondary_tokens = {c.strip() for c in secondary_cities if c.strip()}

        for r in rows:
            jtype = r["job_type"] or "未知"
            src = r["source"] or "unknown"
            by_job_type[jtype] = by_job_type.get(jtype, 0) + 1
            by_source_raw[src] = by_source_raw.get(src, 0) + 1
            bucket = _source_bucket(src)
            by_source_bucket[bucket] = by_source_bucket.get(bucket, 0) + 1

            try:
                cities = json.loads(r["cities_json"] or "[]")
            except json.JSONDecodeError:
                cities = []
            city_blob = " ".join(str(c) for c in cities)
            text_blob = f"{r['company']} {r['title']}".lower()
            is_finance = any(k in text_blob for k in FINANCE_KEYWORDS)

            if any(tok in city_blob for tok in primary_tokens):
                primary_hits += 1
                if is_finance:
                    primary_fin_hits += 1
            elif any(tok in city_blob for tok in secondary_tokens):
                secondary_hits += 1
                if is_finance:
                    secondary_fin_hits += 1

        master_row = conn.execute(
            "SELECT version_tag, profile_json, qa_bank_json FROM master_versions "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        latest_master = None
        bullet_count = 0
        qa_count = 0
        if master_row:
            latest_master = master_row["version_tag"]
            try:
                prof = json.loads(master_row["profile_json"])
                for section in ("experiences", "campus_projects"):
                    for item in prof.get(section, []):
                        bullet_count += len(item.get("bullets", []))
                qa_count = len(json.loads(master_row["qa_bank_json"]).get("items", []))
            except json.JSONDecodeError:
                pass

        run_rows = conn.execute(
            "SELECT id, run_type, status, stats_json, started_at, finished_at "
            "FROM runs ORDER BY id DESC LIMIT 12"
        ).fetchall()
        recent_runs = [
            {
                "id": rr["id"],
                "run_type": rr["run_type"],
                "status": rr["status"],
                "stats": json.loads(rr["stats_json"] or "{}"),
                "started_at": rr["started_at"] or "",
                "finished_at": rr["finished_at"] or "",
            }
            for rr in run_rows
        ]

    return {
        "db_exists": True,
        "total_jobs": len(rows),
        "by_job_type": by_job_type,
        "by_source_bucket": by_source_bucket,
        "by_source_raw": by_source_raw,
        "primary_city_jobs": primary_hits,
        "primary_finance_jobs": primary_fin_hits,
        "secondary_city_jobs": secondary_hits,
        "secondary_finance_jobs": secondary_fin_hits,
        "latest_master_version": latest_master,
        "master_bullet_count": bullet_count,
        "qa_count": qa_count,
        "recent_runs": recent_runs,
    }


def default_progress_spec() -> dict[str, Any]:
    """Return current structured project roadmap synced with job_agent_plan_v2.2."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "project_name": "Job-auto · 双核求职 Agent",
        "subtitle": "2027 届会计本科校招/实习求职自动化 + Antigravity × AI Studio 双核工作流验证",
        "reviewed_on": today,
        "current_stage": "stage6",
        "position": "Stage 0–5 全流程闭环完成；已完成独立 App Demo（V1.5-demo）落地：方案 I（星夜紫藤×霜白）Slim Rail 工作台、0.8s 乐观渲染与 8s 开屏诊断、Sidecar 懒加载与 Electron 瘦身、零配置示例体验数据、GitHub Release 流水线与 P8 加密中转本地 Stub 接口（待选定服务器后零侵入接入）",
        "next_goal": "试用独立 App Demo 并验证交互细节；待确定长期云服务器方案后，将已预留的 P8 云端加密中转接口与 GitHub Release 自动更新正式发布",
        "stages": [
            {
                "id": "phase0",
                "code": "P0",
                "title": "阶段 0：双核工作流与隐私安全底座",
                "state": "complete",
                "summary": "对齐 GitHub 仓库 LI-11230930/Job-auto，落地 .agents 角色技能体系、PreToolUse 隐私阻断钩子、GitHub PR 审查与项目规划 v2.2。",
                "delivered": [
                    "对齐公开 GitHub 仓库 main 分支并完善 .gitignore（严密隔离 .env / vault / data / local / 私人规划）",
                    "建立 AGENTS.md、.agents/rules/dual-core-workflow.md 与 startcycle / write-spec / code-review / ai-studio-sync 技能",
                    "配置 .agents/hooks.json + guard_sensitive_paths.py 拦截敏感路径读取（已验证 4 组用例）",
                    "确认 GEMINI_API_KEY 环境可用（仅验证加载状态与长度）与 wb-bridge (DeepSeek V4.1 / Kimi) 就绪",
                    "完成 config/user_config.yaml、vault/personal_secrets.json 与 master_profile v1.0 锁定",
                ],
                "remaining": [],
                "gate": "敏感路径 100% gitignored + hooks 生效；Gemini 与 WorkBuddy 双备用通道可用。",
                "evidence": [
                    "AGENTS.md",
                    ".agents/rules/dual-core-workflow.md",
                    ".github/workflows/antigravity-review.yml",
                ],
            },
            {
                "id": "stage1",
                "code": "P1",
                "title": "阶段 1：SQLite 底座、Master v1.0 与多数据源聚合",
                "state": "complete",
                "summary": "建成 7 表 WAL SQLite 架构，完成本地校招只读导入、NCSS 24365 / 智联 SSR / 实习僧公开采集、外校统一身份认证门禁排除，以及 Edge 接管采集与进度看板。",
                "delivered": [
                    "建立 Job-auto/job_agent 工程骨架：db.py (7 表)、config.py、master.py、gemini_provider.py、cli.py",
                    "支持配置本地只读 campus_site_jobs_path 并完成非社招岗入库与去重排序",
                    "新增 NCSS 24365 / 智联招聘 / 实习僧公开适配器，并与 is_restricted_university_portal 联动在源头排除外校统一身份认证入口",
                    "新增 Boss直聘 / 前程无忧 51job / 国聘网 人工辅助采集 (collect-browser / takeover-edge / takeover-sweep) 与快照导入",
                    "搭建 local/progress.html 离线可视化监控面板与 job-agent update-progress 自动更新命令",
                ],
                "remaining": [],
                "gate": "pytest 与 ruff check 全绿，多源数据可一键入库并自动刷新进度看板。",
                "evidence": [
                    "Job-auto/job_agent/db.py",
                    "Job-auto/job_agent/sources/base.py",
                    "Job-auto/job_agent/sources/ncss.py",
                    "Job-auto/job_agent/sources/edge_takeover.py",
                    "Job-auto/job_agent/progress.py",
                ],
            },
            {
                "id": "stage2",
                "code": "P2",
                "title": "阶段 2：规则预筛 + AI 评分 + 定制简历 PDF",
                "state": "complete",
                "summary": "依据首选/次选城市偏好、目标方向与外校门禁规则做零成本预筛，再调用大模型/备用通道评分并基于 Master 档案渲染含照片的单页 A4 PDF。",
                "delivered": [
                    "完成多方向与外校门禁预筛器 prefilter.py，零 API 成本过滤无关与受限入口岗位",
                    "完成 AI 评分器 matcher.py（30/10/15/25/20 权重 + 英语水平透明核验）",
                    "完成单页 A4 富样式 PDF 渲染器（带照片/联系栏/pypdf 1 页闭环）与事实核验拦截器 factcheck.py + tailor.py",
                    "已跑通多批次高分定制投递包生成，全部输出 1 页可读 PDF + diff.md + qa.json",
                ],
                "remaining": [],
                "gate": "每条简历子弹均可反查 master_v1.0 bullet_id，无任何捏造数据且恰好单页。",
                "evidence": [
                    "Job-auto/job_agent/stage2/prefilter.py",
                    "Job-auto/job_agent/stage2/matcher.py",
                    "Job-auto/job_agent/stage2/tailor.py",
                    "Job-auto/job_agent/stage2/pdf_render.py",
                ],
            },
            {
                "id": "stage3",
                "code": "P3",
                "title": "阶段 3：FastAPI 本地人工复核工作台与简报系统",
                "state": "complete",
                "summary": "提供纯本地 Web 审核界面，按秋招/校招与实习双赛道分流，支持内嵌单页 PDF 预览、按公司名下载、一键每天流水线与简报导出。",
                "delivered": [
                    "建成 FastAPI 复核工作台 review_server.py (/review、内嵌单页 PDF 预览、按 {company}.pdf 下载)",
                    "支持秋招/校招 vs 实习双赛道筛选、独立待投递清单与分类简报导出 (stage3/digest.py)",
                    "支持 Approve/Later/Reject 写入 decisions 表并自动入列 applications，拒绝原因自动沉淀供周报分析",
                ],
                "remaining": [],
                "gate": "所有高分岗位在未 Approve 前严禁进入投递队列。",
                "evidence": [
                    "Job-auto/job_agent/stage3/review_server.py",
                    "Job-auto/job_agent/stage3/digest.py",
                    "scripts/review.bat",
                ],
            },
            {
                "id": "stage4",
                "code": "P4",
                "title": "阶段 4：投递方式分流、扩展配置联动与追踪队列",
                "state": "complete",
                "summary": "完成 HR 直聊 / 官网网申（兼容原扩展）/ 邮件直投 / 外校受限四路分流，整理按赛道与公司命名的投递包（实际投递动作已交由用户自主执行）。",
                "delivered": [
                    "定位并只读兼容已有扩展 D:\\SKILL\\resume-autofill-extension (v1.1.0 MV3)，导出秋招/实习双档案 JSON",
                    "实现四路分流 classify_delivery_workflow、prepare-delivery ({company}.pdf 归档与清单) 与 cleanup-restricted (累计隔离 560 条外校认证受限岗)",
                    "支持按官方直招简章与企业区域 HR 邮箱升级替换受限渠道，并在队列卡片内嵌公开直投替代链接",
                    "在工作台「投递追踪队列」完成通道徽标、话术复制、Edge 带扩展打开与投递状态流转看板",
                ],
                "remaining": [],
                "gate": "队列分流、扩展包导出、PDF 归档与追踪状态流转稳定可用；投递动作由用户自行掌握。",
                "evidence": [
                    "Job-auto/job_agent/stage4/delivery.py",
                    "Job-auto/job_agent/cli.py",
                    "scripts/open_edge.bat",
                ],
            },
            {
                "id": "stage5",
                "code": "P5",
                "title": "阶段 5：每日流水线、提醒倒计时、周报调参与备用模型",
                "state": "complete",
                "summary": "交付 Stage 5 截止日与超期提醒、秋招 vs 实习转化漏斗周报与调参建议、一键 daily-cycle 流水线，以及 OpenAI-compatible 备用模型自动降级通道。",
                "delivered": [
                    "实现 Stage 5.1 提醒引擎 collect_reminders（高优岗位 7 日截止倒计时、已投超期 7 天跟进、笔面试与受限入口提示）",
                    "实现 Stage 5.2 每周复盘 build_weekly_report（双赛道转化漏斗、拒绝原因分布、可落地调参建议与 .md/.json 导出）",
                    "实现 Stage 3.2/5 一键每日流水线 daily-cycle 与工作台「复盘与提醒」第 5 标签页及 3 个后端 API",
                    "实现 OpenAICompatibleProvider + FallbackLLMProvider 自动降级路由器（对齐 config/extensions.example.yaml）",
                ],
                "remaining": [],
                "gate": "reminders / weekly-report / daily-cycle 与备用 LLM 路由器全量通过 pytest 与实库验证。",
                "evidence": [
                    "Job-auto/job_agent/stage5/analytics.py",
                    "Job-auto/job_agent/stage5/daily_cycle.py",
                    "Job-auto/job_agent/llm/openai_compat.py",
                    "tests/test_stage5_reports.py",
                ],
            },
            {
                "id": "stage6",
                "code": "P6",
                "title": "阶段 6：门面体验重构、技术选型拍板与独立 App Demo (V1.5-demo)",
                "state": "complete",
                "summary": "基于竞品考察与评审批注，交付方案 I（星夜紫藤×霜白）独立桌面 App Demo：重构 0.8s 乐观渲染开屏与 8s 诊断卡、72px Slim Rail 导航、110ms 点击动效与零第三方统计信任引导。",
                "delivered": [
                    "完成 30 款竞品体验考察报告与 6 条评审批注解析，生成《新版开发规划与技术选型方案》",
                    "重构 `desktop/splash.html` + `desktop/main.js`：实现 0.8s 本地快照乐观渲染与 8s Sidecar 超时诊断恢复卡",
                    "重构 `stage3/workbench_ui.py`：落地「方案 I（#2E1065 + #7C3AED + #F9F8FE）」全局 Token、Arc Slim Rail 导航、顶栏 3 主键收纳、110ms GPU 物理反馈与零第三方统计透明横幅",
                    "打通桌面通知（Toast / 应用内消息中心）优先 + SMTP 邮箱兜底链路，独立桌面弹窗完全脱离浏览器依赖",
                ],
                "remaining": [],
                "gate": "首屏冷启动 0.8s 乐观渲染可用；工作台主区无冗余技术术语；零外发埋点网络请求实测通过。",
                "evidence": [
                    "desktop/splash.html",
                    "desktop/main.js",
                    "Job-auto/job_agent/stage3/workbench_ui.py",
                ],
            },
            {
                "id": "stage7",
                "code": "P7",
                "title": "阶段 7：效率闭环、日历月视图与 GitHub 发布就绪 (V1.8)",
                "state": "active",
                "summary": "已完成 5 页桌面独立工作台重构（审阅 / 消息 / 看板 / 复盘 / 设置）、投递截止日历月视图、Ctrl+K 全局命令、零配置游客示例、1.8.0 全仓库版本对齐与本地 NSIS/Portable 打包校验；仅待远程推送 Git Tag 发布首个 GitHub Release。",
                "delivered": [
                    "交付 `demo_seed.py` + `POST /api/system/seed-demo`：内置 3 份脱敏财会岗位与单页定制 PDF，零 API Key 即可跑通完整审阅流程",
                    "交付全局 Ctrl+K 命令面板、3 秒撤销 Toast、后台任务浮窗胶囊、零边距列表/4 列 Kanban/月度截止日历三视图切换",
                    "完成 `1.8.0` 版本对齐（`pyproject.toml`/`desktop/package.json`/`__init__.py`）、`.github/workflows/release.yml` 自动化测试门禁与本地 `portable + nsis + SHA256SUMS` 打包验证",
                ],
                "remaining": [
                    "由维护者执行 `git tag v1.8.0 && git push --tags` 触发 GitHub Actions 首版 Release 构建与分发",
                ],
                "gate": "全量 ruff/pytest/Playwright 与 Windows NSIS/Portable 打包本地全绿；推送 Tag 即可全自动发布首个正式版。",
                "evidence": [
                    "Job-auto/job_agent/demo_seed.py",
                    "Job-auto/job_agent/stage3/workbench_ui.py",
                    "desktop/package.json",
                    ".github/workflows/release.yml",
                ],
            },
            {
                "id": "stage8",
                "code": "P8",
                "title": "阶段 8：端到端加密云端中转、手机审阅、扩展网申回填与关怀模式 (V1.8 收官)",
                "state": "complete",
                "summary": "已打通端到端 AES-256-GCM 双向加密中转（桌面推送 <-> Cloudflare Worker/KV <-> 手机零知识 WebCrypto 审阅页 <-> 回写 SQLite）、Edge 采集与安全网申回填扩展 v1.3.0 及 120% 舒心大字关怀模式。",
                "delivered": [
                    "交付 `cloud_relay.py` 全链路双向同步（`push_packages_to_relay` / `pull_and_apply_relay_actions`），接入 `daily_cycle` 与桌面设置页一键推送/拉取",
                    "交付 `deploy/cloudflare-worker/worker.js`（Worker + KV TTL + `/mobile` HTTPS 客户端）与本地 `/relay-mobile` 零知识 WebCrypto AES-256-GCM 审阅端",
                    "交付 `GET /api/autofill/bundle` 与 `extensions/job_auto_collector/` v1.3.0 网申智能回填与话术复制面板（严格 `autofill-never-submit`）",
                    "上线工作台右上角「120% 舒心大字」高可读关怀模式实时切换",
                ],
                "remaining": [],
                "gate": "Python AESGCM <-> 浏览器 WebCrypto 跨运行时解密/加密全链路实测通过；扩展回填绝不触发表单自动提交。",
                "evidence": [
                    "Job-auto/job_agent/cloud_relay.py",
                    "Job-auto/job_agent/relay_mobile_ui.py",
                    "deploy/cloudflare-worker/worker.js",
                    "extensions/job_auto_collector/popup.js",
                ],
            },
        ],
        "sources_matrix": [
            {
                "bucket": "campus_site",
                "name": "本地校招数据源（可选只读接入）",
                "mode": "自动本地同步",
                "compliance": "根据 user_config.yaml 配置只读读取本地 jobs.json，排除社招与内置示例，绝不写回原目录。",
                "command": "job-agent sync-campus --exclude-social",
            },
            {
                "bucket": "ncss",
                "name": "国家大学生就业服务平台 (NCSS / 24365)",
                "mode": "公开 JSON 自动采集",
                "compliance": "教育部官方公开岗位接口，无需登录与验证码，按配置城市列表低频礼貌拉取公开岗位。",
                "command": "job-agent sync-public --sources ncss",
            },
            {
                "bucket": "zhaopin",
                "name": "智联招聘 (Zhaopin SSR)",
                "mode": "公开 SSR 自动采集 + 人工兜底",
                "compliance": "读取公开搜索页 SSR 状态并过滤资深社招；若遇登录/验证墙立即停机不绕过。",
                "command": "job-agent sync-public --sources zhaopin",
            },
            {
                "bucket": "shixiseng",
                "name": "实习僧 (Shixiseng SSR)",
                "mode": "公开 SSR 自动采集",
                "compliance": "公开 Nuxt SSR 列表抓取财务/会计/审计/ERP 实习岗位。",
                "command": "job-agent sync-public --sources shixiseng",
            },
            {
                "bucket": "iguopin",
                "name": "国聘网 (iguopin.com)",
                "mode": "人工辅助浏览器 / 快照导入",
                "compliance": "接口 /api/jobs/v3/list 返回 403 需登录权限，严禁绕过鉴权；由用户在可见浏览器登录后采集。",
                "command": "job-agent collect-browser --site iguopin",
            },
            {
                "bucket": "zhipin",
                "name": "Boss直聘 (zhipin.com)",
                "mode": "人工辅助浏览器 / 快照导入",
                "compliance": "存在强登录与反爬滑块门禁，严禁隐身插件或自动过验；使用有头浏览器人工辅助抓取当前页。",
                "command": "job-agent collect-browser --site zhipin",
            },
            {
                "bucket": "51job",
                "name": "前程无忧 (51job.com)",
                "mode": "人工辅助浏览器 / 快照导入",
                "compliance": "存在 WAF/滑块门禁；由用户在可见浏览器筛好城市/关键词后一键提取列表卡片。",
                "command": "job-agent collect-browser --site 51job",
            },
            {
                "bucket": "manual",
                "name": "微信公众号 / 官网直链 (split-jd)",
                "mode": "手动录入 / LLM 拆解",
                "compliance": "支持长文粘贴自动拆分多条岗位，或单个官方 JD 文本直接入库。",
                "command": "job-agent split-jd --file jd_post.txt",
            },
        ],
        "gates": [
            {
                "title": "隐私与防幻觉门禁",
                "state": "complete",
                "detail": "PreToolUse 钩子拦截 .env/vault/private；所有定制简历与网申 QA 必须命中 master_v1.0 bullet_id，英语成绩如实写明 CET-4 最高 418（未过）与高考英语 104。",
            },
            {
                "title": "合规采集红线",
                "state": "complete",
                "detail": "Boss直聘 / 前程无忧 / 国聘网 严禁绕过登录、反爬或验证码；统一通过用户可见有头浏览器 collect-browser 或本地保存页面 import-html 合规入库。",
            },
            {
                "title": "双核工作流闭环门禁",
                "state": "active",
                "detail": "Antigravity 本地工程实现 + Google AI Studio / GitHub PR 自动化五维代码审查，确保每个阶段推进都同步更新本进度看板。",
            },
            {
                "title": "零第三方统计与开源分发门禁 (用户批注确认)",
                "state": "active",
                "detail": "全栈 Local-First 运行，严禁接入任何第三方埋点、遥测或数据回传 SDK；安装包与更新源统一走 GitHub Releases，暂不上架商业应用商店。",
            },
        ],
        "milestones": [
            {
                "date": today,
                "title": "Stage 0 · 双核工作流与隐私安全底座落地",
                "detail": "完成 GitHub Job-auto 对齐、.agents 规则技能钩子、config/user_config.yaml、master_profile v1.0 与 .env / wb-bridge 自检。",
                "test_count": 8,
            },
            {
                "date": today,
                "title": "Stage 1 · 多源数据扩展与进度监控面板上线",
                "detail": "接入 NCSS 24365 公开接口、智联公开 SSR、实习僧 SSR、Boss/51job/国聘人工辅助浏览器采集器及 local/progress.html 监控看板。",
                "test_count": None,
            },
        ],
    }


def load_or_init_progress_data(data_path: Path) -> dict[str, Any]:
    if data_path.exists():
        try:
            loaded = json.loads(data_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and "stages" in loaded:
                return loaded
        except json.JSONDecodeError:
            pass
    spec = default_progress_spec()
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec


def update_progress_artifacts(
    *,
    project_root: Path | None = None,
    db_path: Path | None = None,
    milestone_title: str | None = None,
    milestone_detail: str | None = None,
    test_count: int | None = None,
    current_stage: str | None = None,
    position: str | None = None,
    next_goal: str | None = None,
    sync_stages: bool = False,
) -> dict[str, Any]:
    """Refresh local/progress_data.json with live DB metrics and regenerate local/progress.html."""
    root = project_root or get_project_root()
    resolved_db = db_path or (root / "data" / "job_agent.db")
    cfg_override = root / "config" / "user_config.yaml"
    cfg = load_user_config(cfg_override) if cfg_override.is_file() else load_user_config()

    local_dir = root / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    data_path = local_dir / "progress_data.json"
    html_path = local_dir / "progress.html"

    spec = load_or_init_progress_data(data_path)
    if sync_stages:
        fresh = default_progress_spec()
        spec["stages"] = fresh["stages"]
        spec["gates"] = fresh["gates"]
        spec["sources_matrix"] = fresh["sources_matrix"]
        if not current_stage:
            spec["current_stage"] = fresh["current_stage"]
        if not position:
            spec["position"] = fresh["position"]
        if not next_goal:
            spec["next_goal"] = fresh["next_goal"]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    spec["reviewed_on"] = now_str

    if current_stage:
        spec["current_stage"] = current_stage
    if position:
        spec["position"] = position
    if next_goal:
        spec["next_goal"] = next_goal
    if milestone_title:
        milestones = spec.setdefault("milestones", [])
        if milestones and milestones[-1].get("title") == milestone_title:
            milestones[-1] = {
                "date": now_str,
                "title": milestone_title,
                "detail": milestone_detail or milestones[-1].get("detail", ""),
                "test_count": test_count,
            }
        else:
            milestones.append(
                {
                    "date": now_str,
                    "title": milestone_title,
                    "detail": milestone_detail or "",
                    "test_count": test_count,
                }
            )
    elif test_count is not None and spec.get("milestones"):
        spec["milestones"][-1]["test_count"] = test_count

    # Deduplicate accidental adjacent identical milestone entries while keeping history order.
    deduped: list[dict[str, Any]] = []
    for item in spec.get("milestones", []):
        if deduped and deduped[-1].get("title") == item.get("title"):
            deduped[-1] = item
        else:
            deduped.append(item)
    spec["milestones"] = deduped

    live = collect_live_db_metrics(
        resolved_db,
        primary_cities=cfg.preferences.primary_cities,
        secondary_cities=cfg.preferences.secondary_cities,
    )
    payload = {**spec, "live_metrics": live}

    data_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_progress_html(payload), encoding="utf-8")
    return {
        "data_path": str(data_path),
        "html_path": str(html_path),
        "total_jobs": live["total_jobs"],
        "primary_finance_jobs": live["primary_finance_jobs"],
        "secondary_finance_jobs": live["secondary_finance_jobs"],
    }


def render_progress_html(payload: dict[str, Any]) -> str:
    """Render a zero-CDN, CSP-safe interactive progress monitor HTML."""
    # Prevent closing </script> injection inside embedded JSON
    embedded_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none'">
<title>{payload.get('project_name', 'Job-auto')} · 推进监控台</title>
<style>
:root{{
  --bg:#f4f6f5; --paper:#ffffff; --ink:#1d343b; --muted:#63767c;
  --line:#dbe3e2; --teal:#08796e; --teal-soft:#e8f3f1;
  --warn:#a16207; --warn-soft:#fef9c3;
  --plan:#475569; --plan-soft:#f1f5f9;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.62 "Microsoft YaHei","PingFang SC","Segoe UI",sans-serif}}
a{{color:var(--teal);text-decoration:none}} a:hover{{text-decoration:underline}}
.topbar{{background:var(--paper);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}}
.topbar-in{{max-width:1180px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
.brand{{display:flex;align-items:center;gap:9px;font-weight:700;font-size:16px}}
.mark{{width:26px;height:26px;border-radius:7px;background:var(--teal);color:#fff;display:grid;place-items:center;font-size:13px}}
.badge{{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--teal-soft);color:var(--teal);font-weight:600}}
.navtabs{{display:flex;gap:6px;margin-left:10px}}
.navtabs button{{border:1px solid transparent;background:transparent;color:var(--muted);padding:6px 12px;border-radius:7px;cursor:pointer;font:inherit;font-size:13.5px;font-weight:600}}
.navtabs button.active,.navtabs button:hover{{background:var(--teal-soft);color:var(--teal);border-color:#c6e2dd}}
.meta{{margin-left:auto;color:var(--muted);font-size:12.5px;display:flex;align-items:center;gap:10px}}
.btn-sm{{border:1px solid var(--line);background:#fff;color:var(--ink);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px}}
.btn-sm:hover{{border-color:var(--teal);color:var(--teal)}}
.wrap{{max-width:1180px;margin:0 auto;padding:22px 24px 60px}}
.hero{{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--teal);border-radius:10px;padding:18px 22px;margin-bottom:18px}}
.hero .eyebrow{{font-size:11.5px;font-weight:700;letter-spacing:.06em;color:var(--teal);text-transform:uppercase}}
.hero h1{{margin:4px 0 6px;font-size:21px;letter-spacing:-.01em}}
.hero p{{margin:0;color:var(--muted);font-size:14px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
.metric{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.metric .lbl{{font-size:12.5px;color:var(--muted);display:block;margin-bottom:4px}}
.metric .val{{font-size:24px;font-weight:700;color:var(--ink);line-height:1.15}}
.metric .sub{{font-size:12px;color:var(--muted);margin-top:6px}}
.panel{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:18px}}
.panel h2{{margin:0 0 12px;font-size:16.5px;display:flex;align-items:center;justify-content:space-between}}
.stage-map{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}}
.stage-btn{{border:1px solid var(--line);background:#fbfcfc;border-radius:9px;padding:10px 11px;text-align:left;cursor:pointer;transition:.15s;font:inherit}}
.stage-btn:hover{{border-color:var(--teal)}}
.stage-btn.selected{{background:var(--teal-soft);border-color:var(--teal);box-shadow:0 0 0 1px var(--teal) inset}}
.stage-btn .code{{font-size:11px;font-weight:700;color:var(--muted)}}
.stage-btn .stitle{{font-size:13px;font-weight:700;margin:4px 0 6px;line-height:1.3;color:var(--ink)}}
.tag{{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;font-weight:600}}
.tag.complete{{background:#dcfce7;color:#166534}}
.tag.active{{background:var(--teal-soft);color:var(--teal)}}
.tag.partial{{background:var(--warn-soft);color:var(--warn)}}
.tag.planned{{background:var(--plan-soft);color:var(--plan)}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px}}
.box{{border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#fafcfc}}
.box h3{{margin:0 0 8px;font-size:13.5px;color:var(--ink)}}
.box ul{{margin:0;padding-left:18px}}
.box li{{margin:4px 0;font-size:13.5px}}
.gate-bar{{margin-top:12px;padding:10px 14px;border-radius:8px;background:#f7fafa;border:1px solid #d5e5e2;font-size:13.5px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}
.chip{{font-size:12px;padding:2px 8px;border-radius:6px;background:#f1f5f4;border:1px solid var(--line);color:var(--ink);font-family:Consolas,monospace}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{background:#f8fbfa;font-size:12.5px;color:var(--muted);font-weight:600}}
.cmd{{font-family:Consolas,monospace;font-size:12px;background:#f4f7f6;padding:2px 6px;border-radius:4px;border:1px solid var(--line);white-space:nowrap}}
.timeline-item{{border-left:2px solid var(--teal);padding:4px 0 12px 14px;margin-left:6px;position:relative}}
.timeline-item::before{{content:"";width:9px;height:9px;border-radius:50%;background:var(--teal);position:absolute;left:-5.5px;top:7px}}
.timeline-item small{{color:var(--muted);font-size:12px}}
.timeline-item h4{{margin:2px 0 4px;font-size:14.5px}}
.timeline-item p{{margin:0;color:var(--muted);font-size:13px}}
.hidden{{display:none}}
@media(max-width:920px){{.metrics{{grid-template-columns:repeat(2,1fr)}} .stage-map{{grid-template-columns:repeat(2,1fr)}} .two-col{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-in">
    <div class="brand"><div class="mark">J</div><span id="brand-title"></span><span class="badge">仅本地 · CSP 离线</span></div>
    <nav class="navtabs">
      <button class="active" data-tab="overview">总览 & 阶段图</button>
      <button data-tab="sources">数据源矩阵</button>
      <button data-tab="logs">里程碑 & 同步日志</button>
    </nav>
    <div class="meta">
      <span id="reviewed-on"></span>
      <button class="btn-sm" id="export-btn">导出进度 JSON</button>
    </div>
  </div>
</header>

<main class="wrap">
  <section class="hero">
    <div class="eyebrow" id="hero-pos"></div>
    <h1 id="hero-title"></h1>
    <p id="hero-sub"></p>
  </section>

  <section class="metrics" id="kpi-strip"></section>

  <div id="tab-overview">
    <section class="panel">
      <h2><span>开发路线与阶段推进图</span><span style="font-size:12.5px;color:var(--muted);font-weight:400">点击卡片切换阶段详情</span></h2>
      <div class="stage-map" id="stage-map"></div>
      <div id="stage-detail"></div>
    </section>

    <div class="two-col">
      <section class="panel">
        <h2><span>最近交付里程碑</span><span style="font-size:12px;color:var(--muted);font-weight:400">每步推进自动追加</span></h2>
        <div id="milestone-list"></div>
      </section>
      <section class="panel">
        <h2><span>当前核心关卡 & 下一步优先项</span></h2>
        <div id="gates-list"></div>
      </section>
    </div>
  </div>

  <div id="tab-sources" class="hidden">
    <section class="panel">
      <h2><span>多数据源覆盖与合规采集矩阵</span><span id="src-summary" style="font-size:12.5px;color:var(--muted);font-weight:400"></span></h2>
      <div style="overflow-x:auto">
        <table>
          <thead><tr><th>数据源</th><th>实时入库数</th><th>采集模式</th><th>合规与防封说明</th><th>执行命令</th></tr></thead>
          <tbody id="source-rows"></tbody>
        </table>
      </div>
    </section>
  </div>

  <div id="tab-logs" class="hidden">
    <section class="panel">
      <h2><span>SQLite 同步与运行流水（最近 12 次）</span></h2>
      <div style="overflow-x:auto">
        <table>
          <thead><tr><th>Run ID</th><th>任务类型</th><th>状态</th><th>统计详情</th><th>开始时间</th></tr></thead>
          <tbody id="run-rows"></tbody>
        </table>
      </div>
    </section>
  </div>
</main>

<script id="progress-data" type="application/json">{embedded_json}</script>
<script>
(() => {{
  'use strict';
  const data = JSON.parse(document.getElementById('progress-data').textContent);
  const live = data.live_metrics || {{}};
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
  const stateMap = {{ complete: '已完成', active: '当前推进', partial: '部分完成', planned: '待启动' }};

  document.getElementById('brand-title').textContent = data.project_name;
  document.getElementById('reviewed-on').textContent = '刷新时间 ' + data.reviewed_on;
  document.getElementById('hero-pos').textContent = data.position;
  document.getElementById('hero-title').textContent = '下一步焦点：' + data.next_goal;
  document.getElementById('hero-sub').textContent = data.subtitle;

  const doneCount = data.stages.filter((s) => s.state === 'complete').length;
  const activeStage = data.stages.find((s) => s.id === data.current_stage) || data.stages.find((s) => s.state === 'active') || data.stages[0];
  const kpis = [
    {{ lbl: '阶段完成度', val: doneCount + ' / ' + data.stages.length, sub: '当前重点：' + activeStage.code + ' · ' + activeStage.title.split('：')[0] }},
    {{ lbl: '有效岗位总库容', val: (live.total_jobs ?? 0).toLocaleString(), sub: '校招 ' + ((live.by_job_type||{{}})['校招']||0) + ' · 实习 ' + ((live.by_job_type||{{}})['实习']||0) }},
    {{ lbl: '目标城市财务/ERP命中', val: (live.primary_finance_jobs ?? 0) + ' / ' + (live.secondary_finance_jobs ?? 0), sub: '首选城市 ' + (live.primary_city_jobs ?? 0) + ' 岗 · 次选城市 ' + (live.secondary_city_jobs ?? 0) + ' 岗' }},
    {{ lbl: 'Master 履历事实库', val: live.latest_master_version || '未导入', sub: '已锁定 ' + (live.master_bullet_count ?? 0) + ' 条经历子弹 · ' + (live.qa_count ?? 0) + ' 条网申 QA' }},
  ];
  document.getElementById('kpi-strip').innerHTML = kpis.map((k) =>
    `<div class="metric"><span class="lbl">${{esc(k.lbl)}}</span><div class="val">${{esc(k.val)}}</div><div class="sub">${{esc(k.sub)}}</div></div>`
  ).join('');

  let selectedId = activeStage.id;
  function renderStages() {{
    document.getElementById('stage-map').innerHTML = data.stages.map((s) =>
      `<button class="stage-btn ${{s.id === selectedId ? 'selected' : ''}}" data-stage="${{esc(s.id)}}">
        <div class="code">${{esc(s.code)}}</div>
        <div class="stitle">${{esc(s.title.replace(/^阶段\\s*\\d+：/, ''))}}</div>
        <span class="tag ${{esc(s.state)}}">${{esc(stateMap[s.state] || s.state)}}</span>
      </button>`
    ).join('');

    const cur = data.stages.find((s) => s.id === selectedId) || data.stages[0];
    document.getElementById('stage-detail').innerHTML = `
      <div style="padding-top:6px">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <strong style="font-size:16px">${{esc(cur.code)}} · ${{esc(cur.title)}}</strong>
          <span class="tag ${{esc(cur.state)}}">${{esc(stateMap[cur.state] || cur.state)}}</span>
        </div>
        <p style="margin:8px 0 0;color:var(--muted);font-size:14px">${{esc(cur.summary)}}</p>
        <div class="two-col">
          <div class="box">
            <h3>已经具备（${{cur.delivered.length}} 项）</h3>
            ${{cur.delivered.length ? '<ul>' + cur.delivered.map((x) => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '<p style="color:var(--muted);margin:0;font-size:13px">尚待启动</p>'}}
          </div>
          <div class="box">
            <h3>仍需完成（${{cur.remaining.length}} 项）</h3>
            ${{cur.remaining.length ? '<ul>' + cur.remaining.map((x) => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '<p style="color:#166534;margin:0;font-size:13px">本阶段条目已全部闭环 ✓</p>'}}
          </div>
        </div>
        <div class="gate-bar"><strong>阶段验收标准：</strong>${{esc(cur.gate)}}</div>
        ${{cur.evidence && cur.evidence.length ? '<div class="chips">' + cur.evidence.map((e) => '<span class="chip">' + esc(e) + '</span>').join('') + '</div>' : ''}}
      </div>
    `;
  }}
  renderStages();

  document.getElementById('stage-map').addEventListener('click', (e) => {{
    const btn = e.target.closest('[data-stage]');
    if (!btn) return;
    selectedId = btn.dataset.stage;
    renderStages();
  }});

  document.getElementById('milestone-list').innerHTML = [...(data.milestones || [])].reverse().map((m) =>
    `<div class="timeline-item">
      <small>${{esc(m.date)}}${{m.test_count !== null && m.test_count !== undefined ? ' · 测试覆盖 ' + esc(m.test_count) + ' 项' : ''}}</small>
      <h4>${{esc(m.title)}}</h4>
      <p>${{esc(m.detail)}}</p>
    </div>`
  ).join('');

  document.getElementById('gates-list').innerHTML = (data.gates || []).map((g) =>
    `<div class="box" style="margin-bottom:10px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
        <strong>${{esc(g.title)}}</strong>
        <span class="tag ${{esc(g.state)}}">${{esc(stateMap[g.state] || g.state)}}</span>
      </div>
      <p style="margin:0;font-size:13px;color:var(--muted)">${{esc(g.detail)}}</p>
    </div>`
  ).join('');

  const bucketCounts = live.by_source_bucket || {{}};
  document.getElementById('src-summary').textContent = '共覆盖 ' + (data.sources_matrix || []).length + ' 类渠道 · 当前总库 ' + (live.total_jobs ?? 0) + ' 条';
  document.getElementById('source-rows').innerHTML = (data.sources_matrix || []).map((s) => {{
    const cnt = bucketCounts[s.bucket] || 0;
    const statusCls = cnt > 0 ? 'complete' : (s.mode.includes('自动') ? 'active' : 'partial');
    return `<tr>
      <td><strong>${{esc(s.name)}}</strong></td>
      <td><strong>${{cnt}}</strong></td>
      <td><span class="tag ${{statusCls}}">${{esc(s.mode)}}</span></td>
      <td>${{esc(s.compliance)}}</td>
      <td><span class="cmd">${{esc(s.command)}}</span></td>
    </tr>`;
  }}).join('');

  const runs = live.recent_runs || [];
  document.getElementById('run-rows').innerHTML = runs.length ? runs.map((r) =>
    `<tr>
      <td>#${{esc(r.id)}}</td>
      <td><code>${{esc(r.run_type)}}</code></td>
      <td><span class="tag ${{r.status === 'completed' ? 'complete' : 'partial'}}">${{esc(r.status)}}</span></td>
      <td><code>${{esc(JSON.stringify(r.stats))}}</code></td>
      <td>${{esc(r.started_at)}}</td>
    </tr>`
  ).join('') : '<tr><td colspan="5" style="color:var(--muted)">暂无同步运行记录</td></tr>';

  document.querySelectorAll('[data-tab]').forEach((btn) => {{
    btn.addEventListener('click', () => {{
      const tab = btn.dataset.tab;
      document.querySelectorAll('[data-tab]').forEach((b) => b.classList.toggle('active', b === btn));
      ['overview', 'sources', 'logs'].forEach((t) => {{
        document.getElementById('tab-' + t).classList.toggle('hidden', t !== tab);
      }});
    }});
  }});

  document.getElementById('export-btn').addEventListener('click', () => {{
    const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'job-agent-progress.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }});
}})();
</script>
</body>
</html>
"""

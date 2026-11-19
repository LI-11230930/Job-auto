"""Stage 2.1: Deterministic zero-LLM prefilter for campus & intern finance roles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..config import UserConfig
from ..db import Database, normalize_job_type_filter
from ..sources.base import is_restricted_university_portal, normalize_text

FINANCE_INCLUDE_TERMS: tuple[str, ...] = (
    "财务",
    "会计",
    "审计",
    "资金",
    "税务",
    "预算",
    "成本",
    "内控",
    "核算",
    "出纳",
    "总账",
    "财务分析",
    "财务管理",
    "资产",
    "司库",
    "合并报表",
    "erp",
    "用友",
    "金蝶",
    "业财",
    "fpa",
)

EXTENDED_TARGET_INCLUDE_TERMS: tuple[str, ...] = (
    *FINANCE_INCLUDE_TERMS,
    "实施",
    "交付",
    "数据分析",
    "商业分析",
    "数据治理",
    "数据专员",
    "bi",
    "管理",
    "管培",
    "人力",
    "hr",
    "招聘",
    "薪酬",
    "绩效",
    "运营",
    "金融",
    "银行",
    "证券",
    "基金",
    "投研",
    "风控",
    "合规",
    "ai",
    "人工智能",
    "大模型",
    "llm",
    "aigc",
    "智能体",
    "agent",
    "提示词",
    "数智",
)

MT_CONTEXT_TERMS: tuple[str, ...] = (
    "财务",
    "财经",
    "经管",
    "综合",
    "运营",
    "职能",
    "共享中心",
    "管理",
    "人力",
    "数据",
    "金融",
    "ai",
    "数智",
    "行政",
)

NON_FINANCE_BLOCK_TERMS: tuple[str, ...] = (
    "java",
    "c++",
    "golang",
    "前端",
    "后端",
    "embedded",
    "嵌入式",
    "硬件工程师",
    "pcb",
    "ic设计",
    "半导体",
    "临床医学",
    "护理",
    "护士",
    "医生",
    "药师",
    "生鲜销售",
    "教师管培",
    "教培",
    "电话销售",
    "房产经纪",
    "置业顾问",
    "招商专员",
    "美容",
    "美发",
    "厨师",
    "司机",
    "保安",
    "保洁",
    "施工员",
    "测绘",
    "土建",
    "焊接",
    "机械设计",
    "模具",
    "化工工艺",
    "养殖",
    "畜牧",
)


@dataclass(frozen=True)
class PrefilterOutcome:
    rule_pass: bool
    city_tier: str  # primary | secondary | nationwide | mismatch
    rule_score_hint: int
    reject_reason: str


def evaluate_job_prefilter(
    job: dict[str, Any],
    cfg: UserConfig,
    *,
    allow_nationwide: bool = False,
) -> PrefilterOutcome:
    """Deterministically screen one job before spending LLM tokens."""
    from ..filters import evaluate_custom_rules

    cf = cfg.preferences.custom_filter
    active_custom_rules = [
        r for r in cf.rules if r.enabled and [v for v in r.values if str(v).strip()]
    ]

    company = str(job.get("company") or "").strip()
    if any(ex in company for ex in cfg.preferences.excluded_companies):
        return PrefilterOutcome(False, "mismatch", 0, "company_excluded")

    is_restricted, restricted_reason = is_restricted_university_portal(
        source=str(job.get("source") or ""),
        url=str(job.get("url") or ""),
        jd_text=str(job.get("jd_text") or ""),
        apply_channel=str(job.get("apply_channel") or ""),
        apply_target=str(job.get("apply_target") or ""),
    )
    if is_restricted:
        return PrefilterOutcome(
            False, "restricted_portal", 0, f"restricted_university_portal:{restricted_reason}"
        )

    # Full user-controlled override mode: evaluate strictly via user's own criterion rules & threshold
    if cf.enabled and cf.mode == "override" and active_custom_rules:
        eval_res = evaluate_custom_rules(job, cfg)
        return PrefilterOutcome(
            bool(eval_res["passed"]),
            "custom",
            int(eval_res["effective_score"]),
            str(eval_res["reject_reason"] or ""),
        )

    job_type = str(job.get("job_type") or "").strip()
    allowed_types = (
        {normalize_job_type_filter(t) for t in cf.job_types if str(t).strip()} - {"all"}
        if (cf.enabled and cf.job_types)
        else set(cfg.preferences.target_job_types)
    )
    if allowed_types and job_type not in allowed_types:
        return PrefilterOutcome(False, "mismatch", 0, f"job_type_excluded:{job_type}")

    if cf.enabled and cf.sources:
        raw_src = str(job.get("source") or "").strip().lower()
        allowed_src = {s.strip().lower() for s in cf.sources if str(s).strip()}
        src_ok = (raw_src in allowed_src) or (
            "campus_site" in allowed_src and (raw_src.startswith("campus_site") or raw_src == "manual")
        )
        if not src_ok:
            return PrefilterOutcome(False, "mismatch", 0, f"source_excluded:{raw_src}")

    if cf.enabled and cf.apply_channels:
        allowed_ch = {c.strip().lower() for c in cf.apply_channels if str(c).strip()}
        ch_val = str(job.get("apply_channel") or "").strip().lower()
        if allowed_ch and ch_val not in allowed_ch:
            return PrefilterOutcome(False, "mismatch", 0, f"channel_excluded:{ch_val}")

    company = str(job.get("company") or "").strip()
    if any(ex in company for ex in cfg.preferences.excluded_companies):
        return PrefilterOutcome(False, "mismatch", 0, "company_excluded")

    is_restricted, restricted_reason = is_restricted_university_portal(
        source=str(job.get("source") or ""),
        url=str(job.get("url") or ""),
        jd_text=str(job.get("jd_text") or ""),
        apply_channel=str(job.get("apply_channel") or ""),
        apply_target=str(job.get("apply_target") or ""),
    )
    if is_restricted:
        return PrefilterOutcome(
            False, "restricted_portal", 0, f"restricted_university_portal:{restricted_reason}"
        )

    title = str(job.get("title") or "").strip()
    jd_text = str(job.get("jd_text") or "").strip()
    title_low = title.lower()
    joined_low = f"{company} {title} {jd_text}".lower()

    excluded_kws = (
        [*cfg.preferences.excluded_keywords, *cf.excluded_keywords]
        if cf.enabled
        else list(cfg.preferences.excluded_keywords)
    )
    for kw in excluded_kws:
        if kw and kw.lower() in title_low:
            return PrefilterOutcome(False, "mismatch", 0, f"excluded_keyword:{kw}")

    if cf.enabled and cf.include_keywords:
        inc_kws = [k.strip().lower() for k in cf.include_keywords if k.strip()]
        if inc_kws and not any(k in joined_low for k in inc_kws):
            return PrefilterOutcome(False, "mismatch", 0, "missing_include_keyword")

    # City tiering (custom filter overrides if enabled)
    raw_cities = job.get("cities")
    if raw_cities is None and "cities_json" in job:
        try:
            raw_cities = json.loads(job["cities_json"] or "[]")
        except json.JSONDecodeError:
            raw_cities = []
    city_blob = " ".join(str(c) for c in (raw_cities or []))

    custom_cities = [c.strip() for c in cf.custom_cities if str(c).strip()] if cf.enabled else []
    primary_tokens = custom_cities or [c.strip() for c in cfg.preferences.primary_cities if c.strip()]
    secondary_tokens = (
        []
        if (cf.enabled and cf.city_scope == "primary_only")
        else [c.strip() for c in cfg.preferences.secondary_cities if c.strip()]
    )
    effective_nationwide = allow_nationwide or (
        cf.enabled and cf.city_scope in {"all", "allow_nationwide"}
    )

    if any(tok in city_blob for tok in primary_tokens):
        city_tier = "primary"
        city_bonus = 25
    elif any(tok in city_blob for tok in secondary_tokens):
        city_tier = "secondary"
        city_bonus = 18
    elif cf.enabled and cf.city_scope == "all" and not custom_cities:
        city_tier = "nationwide"
        city_bonus = 10
    elif effective_nationwide and (not raw_cities or "全国" in city_blob or "不限" in city_blob):
        city_tier = "nationwide"
        city_bonus = 8
    else:
        return PrefilterOutcome(False, "mismatch", 0, f"city_out_of_scope:{city_blob[:30]}")

    # Multi-domain target check (Accounting/Finance/Audit/ERP/Implementation/Management/HR/Ops/Data/Finance/AI)
    has_core_finance_title = any(k in title_low for k in FINANCE_INCLUDE_TERMS)
    has_target_title = any(k in title_low for k in EXTENDED_TARGET_INCLUDE_TERMS)
    has_target_jd = any(k in joined_low for k in EXTENDED_TARGET_INCLUDE_TERMS)
    is_mt_title = ("管培" in title_low or "培训生" in title_low) and any(
        k in title_low for k in MT_CONTEXT_TERMS
    )
    has_non_target_blocker = any(b in title_low for b in NON_FINANCE_BLOCK_TERMS)

    if has_non_target_blocker and not has_target_title:
        return PrefilterOutcome(False, city_tier, 0, "non_target_domain")
    if not (has_target_title or is_mt_title or has_target_jd):
        return PrefilterOutcome(False, city_tier, 0, "no_target_signal")

    # Compute heuristic ranking hint so highest-fit candidates go to LLM first
    score_hint = 35 + city_bonus
    if has_core_finance_title:
        score_hint += 25
    elif has_target_title:
        score_hint += 20
    if any(k in joined_low for k in ("会计学", "财务管理", "审计", "erp", "用友", "金蝶", "ai", "数据分析", "python")):
        score_hint += 10
    if int(job.get("priority_rank") or 0) >= 20:
        score_hint += 5
    return PrefilterOutcome(True, city_tier, min(100, score_hint), "")


def select_prefilter_candidates(
    db: Database,
    cfg: UserConfig,
    *,
    limit: int | None = None,
    allow_nationwide: bool = False,
    mark_filtered_out: bool = False,
    job_type_filter: str = "all",
) -> tuple[list[tuple[dict[str, Any], PrefilterOutcome]], dict[str, int]]:
    """Run deterministic prefilter across active DB jobs and return ranked candidates."""
    norm_type = normalize_job_type_filter(job_type_filter)
    with db.connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM jobs WHERE status = 'active' ORDER BY priority_rank DESC, id DESC"
            ).fetchall()
        ]

    passed: list[tuple[dict[str, Any], PrefilterOutcome]] = []
    rejected_ids: list[int] = []
    reject_stats: dict[str, int] = {}

    for row in rows:
        outcome = evaluate_job_prefilter(row, cfg, allow_nationwide=allow_nationwide)
        if outcome.rule_pass:
            passed.append((row, outcome))
        else:
            rejected_ids.append(int(row["id"]))
            bucket = outcome.reject_reason.split(":", 1)[0]
            reject_stats[bucket] = reject_stats.get(bucket, 0) + 1

    if mark_filtered_out and rejected_ids:
        with db.connect() as conn:
            conn.executemany(
                "UPDATE jobs SET status = 'filtered_out' WHERE id = ?",
                [(jid,) for jid in rejected_ids],
            )

    passed.sort(
        key=lambda pair: (
            pair[1].rule_score_hint,
            int(pair[0].get("priority_rank") or 0),
            len(pair[0].get("jd_text") or ""),
        ),
        reverse=True,
    )
    # Deduplicate same (company, title, job_type) across multi-university postings before LLM scoring
    deduped: list[tuple[dict[str, Any], PrefilterOutcome]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for pair in passed:
        row = pair[0]
        k = (
            normalize_text(str(row.get("company") or "")),
            normalize_text(str(row.get("title") or "")),
            str(row.get("job_type") or ""),
        )
        if k not in seen_keys:
            seen_keys.add(k)
            deduped.append(pair)

    selected_pool = (
        [pair for pair in deduped if str(pair[0].get("job_type") or "") == norm_type]
        if norm_type != "all"
        else deduped
    )
    selected = selected_pool[:limit] if limit else selected_pool
    stats = {
        "scanned": len(rows),
        "passed": len(passed),
        "unique_passed": len(deduped),
        "selected": len(selected),
        "filtered_out": len(rejected_ids),
        "primary_candidates": sum(1 for _, o in deduped if o.city_tier == "primary"),
        "secondary_candidates": sum(1 for _, o in deduped if o.city_tier == "secondary"),
        "campus_candidates": sum(1 for j, _ in deduped if str(j.get("job_type") or "") == "校招"),
        "intern_candidates": sum(1 for j, _ in deduped if str(j.get("job_type") or "") == "实习"),
    }
    for k, v in reject_stats.items():
        stats[f"reject_{k}"] = v
    return selected, stats

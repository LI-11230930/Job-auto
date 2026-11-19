"""User-defined rule scoring & global custom screening evaluation engine."""

from __future__ import annotations

import json
from typing import Any

from .config import CustomFilterRule, UserConfig
from .db import normalize_job_type_filter

REFERENCE_FILTER_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "ref_city",
        "name": "目标城市匹配",
        "field": "city",
        "match_mode": "multi_any",
        "values": ["太原", "北京", "上海", "成都"],
        "action": "add",
        "score": 25,
        "hint": "填写个人意向城市；命中任一城市即加 25 分（可改为单选具体某城）。",
    },
    {
        "id": "ref_core_role",
        "name": "核心岗位/专业关键词",
        "field": "title",
        "match_mode": "multi_any",
        "values": ["财务", "会计", "审计", "税务", "ERP"],
        "action": "add",
        "score": 30,
        "hint": "岗位名称命中自己目标专业关键词加 30 分（非财会方向可自行替换关键词）。",
    },
    {
        "id": "ref_skills",
        "name": "能力要求/加分技能",
        "field": "any_text",
        "match_mode": "multi_any",
        "values": ["Excel", "Python", "用友", "金蝶", "数据分析"],
        "action": "add",
        "score": 15,
        "hint": "JD 或详情命中自身熟练技能关键词加 15 分。",
    },
    {
        "id": "ref_channel",
        "name": "高响应投递渠道",
        "field": "apply_channel",
        "match_mode": "multi_any",
        "values": ["company_portal", "email"],
        "action": "add",
        "score": 15,
        "hint": "偏好官网网申或邮箱直投（company_portal / email / third_party），命中加 15 分。",
    },
    {
        "id": "ref_growth",
        "name": "平台前景/企业属性",
        "field": "any_text",
        "match_mode": "multi_any",
        "values": ["管培生", "国企", "央企", "上市公司", "可转正"],
        "action": "add",
        "score": 15,
        "hint": "倾向国央企、上市公司或可转正实习等成长特征，命中加 15 分。",
    },
    {
        "id": "ref_hard_req",
        "name": "届别/批次硬门槛",
        "field": "job_type",
        "match_mode": "single",
        "values": ["校招"],
        "action": "require",
        "score": 0,
        "hint": "单选硬门槛示例：未命中直接淘汰，适合严格只看校招或只看实习时使用。",
    },
    {
        "id": "ref_exclude",
        "name": "高危避坑排除词",
        "field": "title",
        "match_mode": "multi_any",
        "values": ["销售", "电销", "催收", "兼职"],
        "action": "exclude",
        "score": 0,
        "hint": "一票排除示例：职位标题包含任意排除词直接淘汰，不占用配额。",
    },
]


def _source_matches(raw_source: str, allowed_sources: list[str]) -> bool:
    if not allowed_sources:
        return True
    low = (raw_source or "").strip().lower()
    allowed_low = {s.strip().lower() for s in allowed_sources if str(s).strip()}
    if not allowed_low:
        return True
    if low in allowed_low:
        return True
    return "campus_site" in allowed_low and (low.startswith("campus_site") or low == "manual")


def _cities_list(item: dict[str, Any]) -> list[str]:
    cities = item.get("cities")
    if isinstance(cities, list):
        return [str(c).strip() for c in cities if str(c).strip()]
    raw = item.get("cities_json")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(c).strip() for c in parsed if str(c).strip()]
        except json.JSONDecodeError:
            pass
    return []


def resolve_filter_city_tokens(cfg: UserConfig) -> list[str]:
    cf = cfg.preferences.custom_filter
    scope = cf.city_scope
    base_primary = [
        c.strip() for c in (cf.custom_cities or cfg.preferences.primary_cities) if str(c).strip()
    ]
    base_secondary = [c.strip() for c in cfg.preferences.secondary_cities if str(c).strip()]
    if scope == "primary_only":
        return list(dict.fromkeys(base_primary))
    if scope in {"primary_and_secondary", "allow_nationwide"}:
        return list(dict.fromkeys([*base_primary, *base_secondary]))
    return list(dict.fromkeys([c.strip() for c in cf.custom_cities if str(c).strip()]))


def _extract_field_tokens(item: dict[str, Any], field: str) -> tuple[str, list[str]]:
    cities = _cities_list(item)
    city_blob = " ".join(cities)
    title = str(item.get("title") or "").strip()
    company = str(item.get("company") or "").strip()
    jd = str(item.get("jd_text") or "").strip()
    job_type = str(item.get("job_type") or "").strip()
    channel = str(item.get("apply_channel") or "").strip()
    source = str(item.get("source") or "").strip()
    factcheck = str(item.get("factcheck_status") or "pass").strip()

    if field == "title":
        return title.lower(), [title.lower()] if title else []
    if field == "company":
        return company.lower(), [company.lower()] if company else []
    if field == "city":
        if cities:
            return city_blob.lower(), [c.lower() for c in cities]
        # Fallback to title when scraper left cities_json empty (common on aggregate campus portals)
        return title.lower(), [title.lower()] if title else []
    if field == "job_type":
        norm = normalize_job_type_filter(job_type)
        toks = [t for t in {job_type.lower(), norm.lower()} if t and t != "all"]
        return " ".join(toks), toks
    if field == "apply_channel":
        return channel.lower(), [channel.lower()] if channel else []
    if field == "source":
        toks = [source.lower()] if source else []
        if source.lower().startswith("campus_site") or source.lower() == "manual":
            toks.append("campus_site")
        return " ".join(toks), toks
    if field == "factcheck_status":
        return factcheck.lower(), [factcheck.lower()] if factcheck else []

    joined = f"{company} {title} {city_blob} {job_type} {channel} {source} {jd}".lower()
    return joined, [joined]


def _rule_matches(item: dict[str, Any], rule: CustomFilterRule) -> tuple[bool, list[str]]:
    values = [str(v).strip() for v in rule.values if str(v).strip()]
    if not values:
        return False, []
    text_blob, exact_tokens = _extract_field_tokens(item, rule.field)
    if rule.match_mode == "single":
        matched = [
            v
            for v in values
            if v.lower() in exact_tokens
            or (rule.field == "city" and any(v.lower() in tok for tok in exact_tokens))
            or (rule.field == "any_text" and v.lower() in text_blob)
        ]
        return len(matched) > 0, matched
    if rule.match_mode == "multi_all":
        matched = [v for v in values if v.lower() in text_blob]
        return len(matched) == len(values), matched
    # default: multi_any
    matched = [v for v in values if v.lower() in text_blob]
    return len(matched) > 0, matched


def evaluate_custom_rules(item: dict[str, Any], cfg: UserConfig) -> dict[str, Any]:
    """Evaluate user-defined rules & global filter bounds cleanly for any job/package."""
    cf = cfg.preferences.custom_filter
    has_base_score = "score" in item and item.get("score") is not None
    raw_item_score = int(item.get("score") or 0) if has_base_score else None

    if not cf.enabled:
        return {
            "passed": True,
            "custom_score": raw_item_score or 0,
            "effective_score": raw_item_score or 0,
            "hits": [],
            "reject_reason": "",
        }

    active_rules = [r for r in cf.rules if r.enabled and [v for v in r.values if str(v).strip()]]
    skip_legacy_kw = cf.mode == "override" and bool(active_rules)

    # 1. Optional top-level scope gates (if user set them alongside rules)
    if cf.job_types:
        allowed_types = {normalize_job_type_filter(t) for t in cf.job_types if str(t).strip()}
        allowed_types.discard("all")
        if allowed_types and normalize_job_type_filter(str(item.get("job_type") or "")) not in allowed_types:
            return {
                "passed": False,
                "custom_score": 0,
                "effective_score": 0,
                "hits": [],
                "reject_reason": f"job_type_excluded:{item.get('job_type', '')}",
            }

    if cf.apply_channels:
        allowed_ch = {str(c).strip().lower() for c in cf.apply_channels if str(c).strip()}
        if allowed_ch and str(item.get("apply_channel") or "").strip().lower() not in allowed_ch:
            return {
                "passed": False,
                "custom_score": 0,
                "effective_score": 0,
                "hits": [],
                "reject_reason": f"channel_excluded:{item.get('apply_channel', '')}",
            }

    if cf.factcheck_statuses and "factcheck_status" in item:
        allowed_fc = {str(s).strip().lower() for s in cf.factcheck_statuses if str(s).strip()}
        if allowed_fc and str(item.get("factcheck_status") or "pass").strip().lower() not in allowed_fc:
            return {
                "passed": False,
                "custom_score": 0,
                "effective_score": 0,
                "hits": [],
                "reject_reason": f"factcheck_excluded:{item.get('factcheck_status', '')}",
            }

    if cf.sources and not _source_matches(str(item.get("source") or ""), cf.sources):
        return {
            "passed": False,
            "custom_score": 0,
            "effective_score": 0,
            "hits": [],
            "reject_reason": f"source_excluded:{item.get('source', '')}",
        }

    # city_scope == "all" means no top-level city gate (stale custom_cities must not trap users)
    if cf.city_scope != "all":
        city_tokens = resolve_filter_city_tokens(cfg)
        cities = _cities_list(item)
        city_blob = " ".join(cities)
        if city_tokens:
            city_hit = any(tok in city_blob for tok in city_tokens)
            if not city_hit and not (
                cf.city_scope == "allow_nationwide"
                and (not cities or "全国" in city_blob or "不限" in city_blob)
            ):
                return {
                    "passed": False,
                    "custom_score": 0,
                    "effective_score": 0,
                    "hits": [],
                    "reject_reason": f"city_out_of_scope:{city_blob[:30]}",
                }

    if not skip_legacy_kw:
        title_low = str(item.get("title") or "").lower()
        joined_low = f"{item.get('company') or ''} {title_low} {item.get('jd_text') or ''}".lower()
        excluded = {
            str(k).strip().lower()
            for k in cf.excluded_keywords
            if str(k).strip()
        }
        if excluded and any(kw in title_low for kw in excluded):
            return {
                "passed": False,
                "custom_score": 0,
                "effective_score": 0,
                "hits": [],
                "reject_reason": "excluded_keyword",
            }
        included = [str(k).strip().lower() for k in cf.include_keywords if str(k).strip()]
        if included and not any(kw in joined_low for kw in included):
            return {
                "passed": False,
                "custom_score": 0,
                "effective_score": 0,
                "hits": [],
                "reject_reason": "missing_include_keyword",
            }

    # 2. User-Defined Custom Rules Engine
    score_delta = 0
    hits: list[dict[str, Any]] = []
    for idx, rule in enumerate(active_rules):
        label = (rule.name or "").strip() or f"规则{idx + 1}"
        matched, matched_vals = _rule_matches(item, rule)
        if rule.action == "exclude":
            if matched:
                return {
                    "passed": False,
                    "custom_score": 0,
                    "effective_score": 0,
                    "hits": [{"name": label, "action": "exclude", "score_delta": 0, "matched": matched_vals}],
                    "reject_reason": f"excluded_rule:{label}",
                }
        elif rule.action == "require":
            if not matched:
                return {
                    "passed": False,
                    "custom_score": 0,
                    "effective_score": 0,
                    "hits": [],
                    "reject_reason": f"missing_required_rule:{label}",
                }
            hits.append({"name": label, "action": "require", "score_delta": 0, "matched": matched_vals})
        elif rule.action == "deduct":
            if matched:
                delta = -int(rule.score or 0)
                score_delta += delta
                hits.append({"name": label, "action": "deduct", "score_delta": delta, "matched": matched_vals})
        else:  # add
            if matched:
                delta = int(rule.score or 0)
                score_delta += delta
                hits.append({"name": label, "action": "add", "score_delta": delta, "matched": matched_vals})

    custom_score = max(0, int(cf.base_score or 0) + score_delta)
    if active_rules:
        if cf.mode == "blend" and raw_item_score is not None:
            effective_score = max(0, raw_item_score + score_delta)
        else:
            effective_score = custom_score
    else:
        effective_score = raw_item_score if raw_item_score is not None else custom_score

    min_score = int(cf.min_display_score or 0)
    if effective_score < min_score:
        # When prefiltering raw jobs without AI score and NO scoring rules exist, allow through unless min_score requires rules
        if not active_rules and raw_item_score is None:
            return {
                "passed": True,
                "custom_score": custom_score,
                "effective_score": custom_score,
                "hits": hits,
                "reject_reason": "",
            }
        return {
            "passed": False,
            "custom_score": custom_score,
            "effective_score": effective_score,
            "hits": hits,
            "reject_reason": f"below_min_score:{effective_score}<{min_score}",
        }

    return {
        "passed": True,
        "custom_score": custom_score,
        "effective_score": effective_score,
        "hits": hits,
        "reject_reason": "",
    }


def matches_custom_filter(item: dict[str, Any], cfg: UserConfig) -> bool:
    """Return True if a review package or job record satisfies active global custom filters."""
    return bool(evaluate_custom_rules(item, cfg)["passed"])


def describe_custom_filter(cfg: UserConfig) -> str:
    """Return a concise human-readable summary of active global custom filters."""
    cf = cfg.preferences.custom_filter
    if not cf.enabled:
        return ""
    parts: list[str] = []
    active_rules = [r for r in cf.rules if r.enabled and [v for v in r.values if str(v).strip()]]
    if active_rules:
        mode_lbl = "接管算分" if cf.mode == "override" else "叠加微调"
        parts.append(f"{len(active_rules)}条自定义规则({mode_lbl})")
    if cf.min_display_score > 0:
        parts.append(f"≥{cf.min_display_score}分")
    if cf.job_types:
        parts.append("/".join(cf.job_types))
    scope_labels = {
        "primary_only": "仅首选城市",
        "primary_and_secondary": "首选+备选城市",
        "allow_nationwide": "含全国不限",
    }
    if cf.city_scope != "all":
        cities = resolve_filter_city_tokens(cfg)
        lbl = scope_labels.get(cf.city_scope, cf.city_scope)
        parts.append(f"{lbl}({','.join(cities[:3])}{'…' if len(cities) > 3 else ''})" if cities else lbl)
    if cf.apply_channels:
        ch_map = {"company_portal": "官网", "third_party": "直聊", "email": "邮箱"}
        parts.append("+".join(ch_map.get(c, c) for c in cf.apply_channels))
    if cf.sources:
        parts.append("来源:" + ",".join(cf.sources[:3]) + ("…" if len(cf.sources) > 3 else ""))
    if cf.include_keywords and not (cf.mode == "override" and active_rules):
        parts.append("必含:" + ",".join(cf.include_keywords[:2]))
    return " · ".join(parts) if parts else "全局自定义规则已开启"

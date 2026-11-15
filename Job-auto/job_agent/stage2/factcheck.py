"""Stage 2.4: Deterministic anti-hallucination & fact-checking rules (§6.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..master import MasterBullet, MasterExperience, MasterProfile

EXAGGERATION_WORDS: tuple[str, ...] = (
    "精通",
    "主导",
    "负责",
    "独立",
    "搭建",
    "从0到1",
    "统筹",
    "操盘",
    "显著提升",
    "核心骨干",
)

FORBIDDEN_INTERN_MARKERS: tuple[str, ...] = (
    "实习经历",
    "任职于",
    "全职实习",
    "企业实习",
)

FORBIDDEN_ENGLISH_FABRICATIONS: tuple[str, ...] = (
    "通过四级",
    "通过大学英语四级",
    "通过cet-4",
    "通过cet4",
    "cet-4通过",
    "cet4通过",
    "通过六级",
    "通过大学英语六级",
    "通过cet-6",
    "通过cet6",
    "cet-6通过",
    "cet6通过",
)

_NUMBER_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?%?")
_TOOL_OR_CERT_TOKENS: tuple[str, ...] = (
    "SAP",
    "Oracle",
    "ORACLE",
    "CPA",
    "ACCA",
    "CMA",
    "CFA",
    "税务师",
    "中级会计",
    "高级会计",
    "CET-6",
    "CET6",
    "雅思",
    "托福",
    "PowerBI",
    "Power BI",
    "Tableau",
    "VBA",
    "SQL",
    "Python",
    "用友U8",
    "金蝶云",
    "金蝶EAS",
    "畅捷通T+",
    "Excel",
    "Word",
    "PPT",
)


@dataclass
class FactCheckReport:
    passed: bool
    status: str  # pass | retry | fallback_raw | blocked
    violations: list[str] = field(default_factory=list)

    def as_feedback(self) -> str:
        return "\n".join(f"- {v}" for v in self.violations)


def _extract_numeric_variants(text: str) -> set[str]:
    """Build acceptable numeric surface tokens from source facts and text."""
    tokens = set(_NUMBER_TOKEN_RE.findall(text or ""))
    expanded = set(tokens)
    for tok in tokens:
        if tok.endswith("%"):
            expanded.add(tok[:-1])
        # Zero-padded date parts like 07 -> 7
        stripped = tok.lstrip("0") or "0"
        expanded.add(stripped)
        expanded.add(tok)
    return expanded


def _collect_bullet_index(profile: MasterProfile) -> dict[str, tuple[MasterExperience, MasterBullet]]:
    index: dict[str, tuple[MasterExperience, MasterBullet]] = {}
    for exp in profile.experiences:
        for bullet in exp.bullets:
            index[bullet.id] = (exp, bullet)
    return index


def _allowed_proper_nouns_lower(profile: MasterProfile) -> set[str]:
    allowed = {
        *(p.lower() for p in profile.proper_nouns_whitelist),
        *(c.lower() for c in profile.certifications),
        *(s.name.lower() for s in profile.skills),
        profile.education.school.lower(),
        profile.education.major.lower(),
    }
    return {x for x in allowed if x}


def verify_tailored_resume(
    tailor_output: dict[str, Any],
    profile: MasterProfile,
    *,
    job_type: str = "校招",
) -> FactCheckReport:
    """Strictly verify tailored resume bullets and summary against MasterProfile (§6.3)."""
    violations: list[str] = []
    bullet_index = _collect_bullet_index(profile)
    selected = tailor_output.get("selected") or []
    summary = str(tailor_output.get("summary") or "").strip()

    if not isinstance(selected, list) or not selected:
        return FactCheckReport(False, "blocked", ["selected 列表为空，缺少有效要点。"])

    allowed_tools = _allowed_proper_nouns_lower(profile)
    global_fact_nums: set[str] = {str(profile.education.graduation_year), "2027", "418", "104", "4"}

    for idx, entry in enumerate(selected, start=1):
        if not isinstance(entry, dict):
            violations.append(f"第 {idx} 项格式非法")
            continue
        bid = str(entry.get("id") or "").strip()
        rewritten = str(entry.get("rewritten") or "").strip()
        if bid not in bullet_index:
            violations.append(f"要点 id '{bid}' 不存在于 Master 档案中")
            continue
        if not rewritten:
            violations.append(f"要点 '{bid}' 改写内容为空")
            continue

        exp, orig_bullet = bullet_index[bid]

        # 1. Numeric whitelist per bullet (facts + original text + experience period)
        allowed_nums = (
            _extract_numeric_variants(" ".join(orig_bullet.facts))
            | _extract_numeric_variants(orig_bullet.text)
            | _extract_numeric_variants(exp.period)
        )
        global_fact_nums |= allowed_nums

        for num in _NUMBER_TOKEN_RE.findall(rewritten):
            if num not in allowed_nums and num.lstrip("0") not in allowed_nums:
                violations.append(
                    f"要点 '{bid}' 出现未在 facts 白名单中的数字 '{num}'"
                )

        # 2. Exaggeration / role-inflation word blocklist
        for word in EXAGGERATION_WORDS:
            if word in rewritten and word not in orig_bullet.text:
                violations.append(
                    f"要点 '{bid}' 新增了原句未出现的夸大/主导词 '{word}'"
                )

        # 3. Campus project / training must NOT be framed as company internship
        if exp.category in {"project", "training"}:
            for marker in FORBIDDEN_INTERN_MARKERS:
                if marker in rewritten and marker not in orig_bullet.text:
                    violations.append(
                        f"要点 '{bid}' 属于 {exp.category}，禁止改写为 '{marker}'"
                    )

        # 4. Tool / certificate whitelist
        rewritten_low = rewritten.lower()
        for tool in _TOOL_OR_CERT_TOKENS:
            if tool.lower() in rewritten_low and (
                tool.lower() not in allowed_tools
                and tool.lower() not in orig_bullet.text.lower()
            ):
                violations.append(
                    f"要点 '{bid}' 出现 Master 白名单之外的软件或证书 '{tool}'"
                )

    # Check summary for numbers, exaggerations, tools, English fabrication, & job_type rules
    all_orig_text = " ".join(b.text for exp in profile.experiences for b in exp.bullets)
    summary_low = summary.lower()

    for num in _NUMBER_TOKEN_RE.findall(summary):
        if num not in global_fact_nums and num.lstrip("0") not in global_fact_nums:
            violations.append(f"个人定位摘要 summary 出现未经核实的数字 '{num}'")

    for word in EXAGGERATION_WORDS:
        if word in summary and word not in all_orig_text:
            violations.append(f"个人定位摘要 summary 出现禁用夸大词 '{word}'")

    for tool in _TOOL_OR_CERT_TOKENS:
        if tool.lower() in summary_low and tool.lower() not in allowed_tools:
            violations.append(f"个人定位摘要 summary 出现白名单外软件/证书 '{tool}'")

    joined_all_low = f"{summary_low} " + " ".join(
        str(x.get("rewritten") or "").lower() for x in selected if isinstance(x, dict)
    )
    for fab in FORBIDDEN_ENGLISH_FABRICATIONS:
        if fab in joined_all_low:
            violations.append(f"违规虚构英语四六级通过表述：'{fab}'")

    if job_type == "校招" and any(k in joined_all_low for k in ("最快", "到岗", "连续稳定实习")):
        violations.append("目标为校招全职，禁止加入短期实习到岗时间表述")

    if violations:
        return FactCheckReport(False, "retry", violations)
    return FactCheckReport(True, "pass", [])

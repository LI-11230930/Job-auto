"""Tests for Edge CDP takeover helper functions."""

from __future__ import annotations

from job_agent.sources.edge_takeover import (
    DEFAULT_SWEEP_SHIXISENG_QUERIES,
    DEFAULT_SWEEP_ZHAOPIN_FILTERS,
    detect_tab_site,
    is_gated_page,
)


def test_detect_tab_site_and_gate_checks() -> None:
    assert detect_tab_site("https://www.zhipin.com/web/geek/job?query=财务") == "zhipin"
    assert detect_tab_site("https://sou.zhaopin.com/?jl=576&kw=AI") == "zhaopin"
    assert detect_tab_site("https://www.shixiseng.com/interns?keyword=审计") == "shixiseng"
    assert detect_tab_site("https://we.51job.com/pc/search") == "51job"
    assert detect_tab_site("https://www.iguopin.com/job") == "iguopin"
    assert detect_tab_site("https://www.baidu.com/") == ""

    assert is_gated_page("https://login.zhipin.com/", "welcome") is True
    assert is_gated_page("https://www.zhipin.com/web/geek/job", "请完成滑动验证后继续") is True
    assert is_gated_page("https://www.zhipin.com/web/geek/job", "太原 财务管培生") is False


def test_default_sweep_targets_cover_target_cities_and_roles() -> None:
    cities = {c for c, _, _ in DEFAULT_SWEEP_SHIXISENG_QUERIES}
    kws = {kw for _, kw, _ in DEFAULT_SWEEP_SHIXISENG_QUERIES}
    assert {"太原", "济南", "青岛", "西安", "全国"}.issubset(cities)
    assert {"会计", "审计", "财务分析", "实施", "管培", "人力资源", "运营", "数据分析", "金融", "AI"}.issubset(kws)
    zp_filters = {name for name, _ in DEFAULT_SWEEP_ZHAOPIN_FILTERS}
    assert {"", "会计学", "财务管理", "人力资源管理", "金融学"}.issubset(zp_filters)

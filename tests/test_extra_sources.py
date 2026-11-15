"""Tests for NCSS, Zhaopin SSR, Shixiseng SSR, HTML snapshot import, and assisted browser normalizer."""

from __future__ import annotations

import json
from pathlib import Path

from job_agent.sources.assisted_browser import normalize_dom_rows
from job_agent.sources.html_import import extract_jobs_from_snapshot, import_snapshot_path
from job_agent.sources.ncss import parse_ncss_payload
from job_agent.sources.shixiseng import parse_shixiseng_html
from job_agent.sources.zhaopin_public import parse_zhaopin_html


def test_parse_ncss_payload_extracts_campus_and_intern() -> None:
    payload = {
        "flag": True,
        "data": {
            "list": [
                {
                    "jobId": "JOB123",
                    "jobName": "财务管理岗",
                    "recName": "中铁三局集团有限公司",
                    "areaCodeName": "山西",
                    "recruitType": "0",
                    "degreeName": "本科及以上",
                    "major": "会计学,财务管理",
                    "lowMonthPay": 6.0,
                    "highMonthPay": 8.0,
                    "recProperty": "国有企业",
                    "recScale": "5000以上",
                    "publishDate": 1794495600000,
                },
                {
                    "jobId": "JOB456",
                    "jobName": "审计实习生",
                    "recName": "太原某会计师事务所",
                    "areaCodeName": "太原",
                    "recruitType": "1",
                    "sourcesType": "0",
                    "sourcesNameCh": "智联招聘",
                },
                {
                    "jobId": "JOB789",
                    "jobName": "财务管培生",
                    "recName": "某受限国企",
                    "areaCodeName": "太原",
                    "recruitType": "0",
                    "sourcesType": "12",
                    "sourcesNameCh": "中南大学",
                },
                {
                    "jobId": "JOB999",
                    "jobName": "会计专员",
                    "recName": "绵阳某科技企业",
                    "areaCodeName": "绵阳",
                    "recruitType": "0",
                    "sourcesType": "12",
                    "sourcesNameCh": "示范大学",
                },
            ]
        },
    }
    jobs = parse_ncss_payload(payload, fallback_city="太原", allowed_schools=("示范大学",))
    assert len(jobs) == 3
    assert [j["source_job_id"] for j in jobs] == ["JOB123", "JOB456", "JOB999"]
    assert jobs[0]["source"] == "ncss"
    assert jobs[0]["job_type"] == "校招"
    assert jobs[0]["cities"] == ["太原", "山西"]
    assert jobs[0]["url"] == "https://www.ncss.cn/student/jobs/JOB123/detail.html"
    assert jobs[0]["apply_channel"] == "third_party"
    assert jobs[1]["job_type"] == "实习"
    assert jobs[2]["company"] == "绵阳某科技企业"

    # Also verify opt-out preserves all entries when explicitly requested.
    all_jobs = parse_ncss_payload(payload, fallback_city="太原", exclude_restricted_campus=False)
    assert len(all_jobs) == 4


def test_parse_zhaopin_html_filters_social_and_detects_gate() -> None:
    state = {
        "positionList": [
            {
                "name": "财务管培生（27届）",
                "companyName": "海信集团",
                "workCity": "青岛",
                "cityDistrict": "崂山",
                "workingExp": "经验不限",
                "education": "本科",
                "salary60": "8000-12000元",
                "positionURL": "https://www.zhaopin.com/jobdetail/ZP1.htm",
                "skillLabel": [{"value": "上市公司"}],
            },
            {
                "name": "资深财务经理",
                "companyName": "某公司",
                "workCity": "太原",
                "workingExp": "5-10年",
                "positionURL": "https://www.zhaopin.com/jobdetail/ZP2.htm",
            },
        ]
    }
    html_ok = f"<html><script>window.__INITIAL_STATE__={json.dumps(state, ensure_ascii=False)};</script></html>"
    jobs, gated = parse_zhaopin_html(html_ok, exclude_social=True)
    assert gated is False
    assert len(jobs) == 1
    assert jobs[0]["company"] == "海信集团"
    assert jobs[0]["job_type"] == "校招"
    assert jobs[0]["cities"] == ["青岛"]

    gated_jobs, gated_flag = parse_zhaopin_html(
        "<html><body>请完成滑动验证</body></html>",
        final_url="https://passport.zhaopin.com/login",
    )
    assert gated_jobs == []
    assert gated_flag is True


def test_parse_shixiseng_html_cleans_pua_icons() -> None:
    sample_html = """
    <div data-intern-id="inn_abc123" class="intern-item">
      <a href="https://www.shixiseng.com/intern/inn_abc123" class="title ellipsis font">财&#x52a1;\ue001实习生</a>
      <a title="山西建投集团" href="javascript:;" class="title ellipsis">山西建投集团</a>
      <span class="city ellipsis">太原</span>
    </div>
    """
    jobs = parse_shixiseng_html(sample_html)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "财务实习生"
    assert jobs[0]["company"] == "山西建投集团"
    assert jobs[0]["cities"] == ["太原"]
    assert jobs[0]["job_type"] == "实习"


def test_extract_snapshots_for_zhipin_51job_and_iguopin(tmp_path: Path) -> None:
    zhipin_html = """
    <ul class="job-list-box">
      <li class="job-card-wrapper">
        <a href="/job_detail/zp_001.html"><span class="job-name">会计实习生</span></a>
        <span class="salary">3-4K</span>
        <span class="job-area">太原·小店区</span>
        <h3 class="company-name"><a href="/gongsi/1.html">太原某财务公司</a></h3>
        <ul><li>在校/应届</li><li>本科</li></ul>
      </li>
    </ul>
    """
    jobs_zp = extract_jobs_from_snapshot(zhipin_html, site="auto")
    assert len(jobs_zp) == 1
    assert jobs_zp[0]["source"] == "zhipin"
    assert jobs_zp[0]["job_type"] == "实习"
    assert "太原" in jobs_zp[0]["cities"][0]

    job51_html = """
    <div class="j_joblist">
      <div class="joblist-item">
        <a class="jname" title="财务专员（2027校招）" href="https://jobs.51job.com/taiyuan/123.html">财务专员（2027校招）</a>
        <a class="cname" title="晋能控股">晋能控股</a>
        <span class="area">太原</span>
        <span class="sal">6-8千</span>
      </div>
    </div>
    """
    (tmp_path / "51job_taiyuan.html").write_text(job51_html, encoding="utf-8")
    imported = import_snapshot_path(tmp_path, site="auto")
    assert len(imported) == 1
    assert imported[0]["source"] == "51job"
    assert imported[0]["company"] == "晋能控股"
    assert imported[0]["job_type"] == "校招"

    iguopin_json = json.dumps(
        {
            "code": 200,
            "data": {
                "list": [
                    {
                        "id": "GP999",
                        "job_name": "财务会计（校园招聘）",
                        "company_name": "中国中铁电气化局",
                        "district_names": "太原,西安",
                    }
                ]
            },
        },
        ensure_ascii=False,
    )
    jobs_gp = extract_jobs_from_snapshot(iguopin_json, site="iguopin")
    assert len(jobs_gp) == 1
    assert jobs_gp[0]["url"] == "https://www.iguopin.com/job/detail/GP999"
    assert jobs_gp[0]["cities"] == ["太原", "西安"]


def test_normalize_assisted_browser_dom_rows() -> None:
    rows = [
        {
            "title": "ERP实施顾问（2027校招）",
            "company": "用友网络山西分公司",
            "city": "太原",
            "salary": "7-10K",
            "tags": ["应届生", "本科"],
            "url": "https://www.zhipin.com/job_detail/erp1.html",
        }
    ]
    jobs = normalize_dom_rows(rows, site="zhipin")
    assert len(jobs) == 1
    assert jobs[0]["source"] == "zhipin"
    assert jobs[0]["job_type"] == "校招"
    assert jobs[0]["cities"] == ["太原"]


def test_extract_zhaopin_logged_in_spa_dom_snapshot() -> None:
    zhaopin_spa = """
    <div class="position-list">
      <div class="position-list__item">
        <div class="position-card" data-sensors-exposure-option="{&quot;properties&quot;:{&quot;jdno&quot;:&quot;CC166275810J40926060303&quot;}}">
          <div class="position-card__job-name">物料成本财务专员（2027届校招）</div>
          <div class="position-card__city-name">「太原」</div>
          <div class="position-card__salary">面议</div>
          <ul class="position-card__tags"><li class="position-card__tags__item">校园</li><li class="position-card__tags__item">本科</li></ul>
          <div class="position-card__company__name">无锡先导智能装备股份有限公司</div>
          <div class="position-card__company__tabs-item">工业自动化</div>
        </div>
      </div>
    </div>
    """
    jobs = extract_jobs_from_snapshot(zhaopin_spa, filename_hint="zhaopin.com/campus")
    assert len(jobs) == 1
    assert jobs[0]["source"] == "zhaopin"
    assert jobs[0]["title"] == "物料成本财务专员（2027届校招）"
    assert jobs[0]["company"] == "无锡先导智能装备股份有限公司"
    assert jobs[0]["cities"] == ["太原"]
    assert jobs[0]["job_type"] == "校招"
    assert jobs[0]["url"] == "https://jobs.zhaopin.com/CC166275810J40926060303.htm"

"""Tests for the read-only campus site adapter."""

from __future__ import annotations

import json
from itertools import islice
from pathlib import Path

from job_agent.sources.campus_site_readonly import CampusSiteReadonlyAdapter


def test_adapter_normalizes_and_skips_sample_rows(tmp_path: Path) -> None:
    sample_file = tmp_path / "jobs.json"
    sample_file.write_text(
        json.dumps(
            [
                {
                    "id": "demo-1",
                    "source": "内置示例",
                    "company": "演示公司",
                    "position": "财务专员",
                    "batch": "秋招",
                },
                {
                    "id": "real-1",
                    "source": "givemeoc",
                    "source_id": "101",
                    "company": "联合利华",
                    "position": "财务管培生",
                    "batch": "2027秋招",
                    "location": "上海、北京",
                    "industry": "快消",
                    "target_graduation": "2027届",
                    "deadline": "2026-12-01",
                    "apply_url": "https://unilever.beisen.com/campus/101",
                    "description": "财务轮岗培养",
                    "requirements": "本科及以上，会计学优先",
                    "status": "进行中",
                },
                {
                    "id": "real-2",
                    "source": "tencent_careers",
                    "source_id": "999",
                    "company": "腾讯",
                    "position": "销售经理",
                    "batch": "社招",
                    "location": "深圳",
                    "apply_url": "https://careers.tencent.com/jobdesc.html?postId=999",
                    "status": "进行中",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    adapter = CampusSiteReadonlyAdapter(sample_file, exclude_social=True)
    rows = list(adapter.fetch_jobs())
    assert len(rows) == 1
    job = rows[0]
    assert job["company"] == "联合利华"
    assert job["cities"] == ["上海", "北京"]
    assert job["job_type"] == "校招"
    assert job["apply_channel"] == "company_portal"
    assert "【岗位职责】" in job["jd_text"]
    assert "【面向届别】2027届" in job["jd_text"]


def test_real_campus_site_readonly_smoke(tmp_path: Path) -> None:
    import os

    env_path = os.getenv("JOB_AUTO_CAMPUS_JSON", "").strip()
    target = Path(env_path) if env_path else (tmp_path / "jobs.json")
    if not target.exists():
        # Create a clean multi-record fixture when no external dataset path is supplied
        payload = [
            {
                "id": f"c-{i}",
                "company": f"示例校招企业{i}",
                "title": "财务管培生" if i % 2 == 0 else "审计助理",
                "tags": ["2027届校招"],
                "locations": ["北京"],
                "url": f"https://example.com/jobs/{i}",
            }
            for i in range(30)
        ]
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    adapter = CampusSiteReadonlyAdapter(target, exclude_social=True)
    sample = list(islice(adapter.fetch_jobs(), 25))
    assert len(sample) == 25
    assert all(row["company"] and row["title"] and row["dedup_hash"] for row in sample)

"""Tests for Stage 1.1 Master profile validation and Stage 1.4 manual JD ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from job_agent.db import Database
from job_agent.llm.base import PromptAsset
from job_agent.master import load_master_and_qa
from job_agent.sources.manual_ingest import build_manual_job, split_summary_post


class FakeLLM:
    def generate_json(
        self,
        *,
        asset: PromptAsset,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        return {
            "jobs": [
                {
                    "company": "示例国企",
                    "title": "财务管培生",
                    "cities": ["太原", "北京"],
                    "job_type": "校招",
                    "jd_text": "轮岗财务各模块",
                    "apply_target": "https://example.beisen.com/campus/1",
                    "deadline": "2026-12-15",
                },
                {
                    "company": "示例制造",
                    "title": "财务助理",
                    "cities": ["上海"],
                    "job_type": "校招",
                    "jd_text": "成本核算",
                    "apply_target": "hr@example.com",
                    "deadline": "",
                },
            ]
        }


def test_master_qa_reference_validation(tmp_path: Path) -> None:
    profile_path = tmp_path / "master.json"
    qa_path = tmp_path / "qa.json"
    profile_path.write_text(
        json.dumps(
            {
                "version_tag": "v1",
                "education": {
                    "school": "示范财经大学",
                    "major": "会计学",
                    "degree": "本科",
                    "period": "2023.09-2027.06",
                },
                "experiences": [
                    {
                        "id": "e1",
                        "category": "internship",
                        "organization": "公司A",
                        "role": "助理",
                        "period": "2026.07",
                        "bullets": [{"id": "b1", "text": "完成核对", "tags": [], "facts": []}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    qa_path.write_text(
        json.dumps(
            {
                "version_tag": "v1",
                "items": [
                    {
                        "id": "q1",
                        "question": "自我介绍",
                        "category": "intro",
                        "draft_answer": "文本",
                        "evidence_ids": ["missing_id"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown bullet ids"):
        load_master_and_qa(profile_path, qa_path)


def test_manual_single_and_split_ingest(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    db.init_schema()

    single = build_manual_job(
        company="华为",
        title="财经专员",
        jd_text="财务核算与分析",
        cities="深圳/上海",
        url="https://career.huawei.com/1",
    )
    split_jobs = split_summary_post(
        raw_text="汇总推文...",
        llm=FakeLLM(),
        prompts_root=Path(__file__).resolve().parents[1] / "prompts",
    )
    res = db.upsert_jobs([single, *split_jobs])
    assert res["inserted"] == 3
    assert db.count_jobs() == 3

"""Tests for configuration loading and AI Studio prompt asset integrity."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from job_agent.config import ScoringWeights, get_project_root, load_user_config
from job_agent.llm.base import load_prompt_asset


def test_load_user_config_and_weights() -> None:
    cfg = load_user_config(get_project_root() / "config" / "user_config.example.yaml")
    assert cfg.scoring.min_score_for_package == 80
    assert cfg.notifications.provider == "email_smtp"
    assert cfg.delivery.priority_ats_systems == ["beisen"]

    with pytest.raises(ValidationError):
        ScoringWeights(
            major_fit=50,
            hard_requirements=50,
            skills_experience=10,
            city_preference=0,
            growth_potential=0,
        )


def test_all_prompt_assets_load_cleanly() -> None:
    prompts_dir: Path = get_project_root() / "prompts"
    for task in ("job_match", "resume_tailor", "jd_split"):
        asset = load_prompt_asset(prompts_dir, task)
        assert asset.task == task
        assert asset.system_instruction
        assert asset.response_schema["type"] == "object"

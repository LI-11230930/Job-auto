"""Configuration schema and loader for Job-auto."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class DataSourcesConfig(BaseModel):
    campus_site_jobs_path: str = ""
    campus_site_readonly: bool = True
    enable_extra_public_sources: bool = True
    extra_csv_paths: list[str] = Field(default_factory=list)


class EnglishStatusConfig(BaseModel):
    cet4_passed: bool = False
    cet4_best_score: int | None = None
    cet6_passed: bool = False
    gaokao_english: str = ""


class ProfileConfig(BaseModel):
    resume_path: str = ""
    graduation_year: int = 2027
    degree: str = "本科"
    major: str = "会计学"
    target_roles: list[str] = Field(
        default_factory=lambda: ["财务培训生", "财务管培生", "管培生（财务方向）"]
    )
    certifications: list[str] = Field(default_factory=list)
    english_status: EnglishStatusConfig = Field(default_factory=EnglishStatusConfig)
    intern_availability: str = ""
    vault_dir: str = "./vault"


class CustomFilterRule(BaseModel):
    id: str = ""
    name: str = ""
    enabled: bool = True
    field: Literal[
        "any_text",
        "title",
        "company",
        "city",
        "job_type",
        "apply_channel",
        "source",
        "factcheck_status",
    ] = "any_text"
    match_mode: Literal["single", "multi_any", "multi_all"] = "multi_any"
    values: list[str] = Field(default_factory=list)
    action: Literal["add", "deduct", "require", "exclude"] = "add"
    score: int = Field(default=20, ge=0, le=200)


class CustomFilterConfig(BaseModel):
    enabled: bool = False
    mode: Literal["override", "blend"] = "override"
    base_score: int = Field(default=0, ge=0, le=100)
    min_display_score: int = Field(default=0, ge=0, le=200)
    rules: list[CustomFilterRule] = Field(default_factory=list)
    city_scope: Literal["all", "primary_only", "primary_and_secondary", "allow_nationwide"] = "all"
    custom_cities: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    apply_channels: list[str] = Field(default_factory=list)
    factcheck_statuses: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    include_keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)


class PreferencesConfig(BaseModel):
    target_job_types: list[str] = Field(default_factory=lambda: ["校招", "实习"])
    primary_cities: list[str] = Field(default_factory=list)
    secondary_cities: list[str] = Field(default_factory=list)
    preferred_industries: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=lambda: ["销售", "电销", "催收", "兼职"])
    custom_filter: CustomFilterConfig = Field(default_factory=CustomFilterConfig)


class ScoringWeights(BaseModel):
    major_fit: int = 30
    hard_requirements: int = 10
    skills_experience: int = 15
    city_preference: int = 25
    growth_potential: int = 20

    @model_validator(mode="after")
    def _check_total_100(self) -> ScoringWeights:
        total = (
            self.major_fit
            + self.hard_requirements
            + self.skills_experience
            + self.city_preference
            + self.growth_potential
        )
        if total != 100:
            raise ValueError(f"Scoring weights must sum to 100, got {total}")
        return self


class ScoringConfig(BaseModel):
    min_score_for_package: int = Field(default=80, ge=0, le=100)
    daily_top_n: int = Field(default=50, ge=1)
    weights: ScoringWeights = Field(default_factory=ScoringWeights)


class LLMConfig(BaseModel):
    primary_provider: str = "gemini_interactions"
    base_url: str = ""
    default_model: str = "gemini-3.5-flash-lite"
    reasoning_model: str = "gemini-3.5-flash-lite"
    lite_model: str = "gemini-3.5-flash-lite"
    api_key_env: str = "GEMINI_API_KEY"
    fallback_enabled: bool = False
    fallback_provider: str = "openai_compat"
    fallback_base_url: str = ""
    fallback_model: str = ""
    fallback_api_key_env: str = "FALLBACK_LLM_API_KEY"


class ChannelModes(BaseModel):
    email: Literal["manual", "assist", "auto"] = "assist"
    company_portal: Literal["manual", "assist", "auto"] = "assist"
    third_party: Literal["manual", "assist", "auto"] = "manual"


class DeliveryConfig(BaseModel):
    follow_company_channel: bool = True
    channel_modes: ChannelModes = Field(default_factory=ChannelModes)
    priority_ats_systems: list[str] = Field(default_factory=lambda: ["beisen"])
    daily_submit_limit: int = Field(default=20, ge=1)
    min_interval_seconds: int = Field(default=30, ge=0)


class NotificationsConfig(BaseModel):
    strategy: Literal["app_first", "app_and_email", "app_only", "email_only"] = "app_first"
    desktop_notify_enabled: bool = True
    push_preset: str = "none"
    push_webhook_env: str = "PUSH_WEBHOOK_URL"
    provider: Literal["email_smtp", "webhook", "none"] = "email_smtp"
    email_preset: str = "qq"
    email_to: str = ""
    smtp_host: str = ""
    smtp_port: int | None = None
    smtp_security: Literal["auto", "ssl", "starttls", "none"] = "auto"
    smtp_host_env: str = "SMTP_HOST"
    smtp_port_env: str = "SMTP_PORT"
    smtp_user_env: str = "SMTP_USER"
    smtp_pass_env: str = "SMTP_PASS"
    urgent_webhook_enabled: bool = False


class CloudRelayConfig(BaseModel):
    """Pluggable zero-knowledge cloud relay interface (P8 deferred server adapter)."""

    enabled: bool = False
    provider: Literal["none", "cloudflare_worker", "custom_http"] = "none"
    endpoint_url: str = ""
    pairing_id: str = ""
    relay_secret_env: str = "CLOUD_RELAY_SECRET"
    ttl_days: int = Field(default=7, ge=1, le=30)
    auto_fallback_to_email: bool = True


class CompanyCheckConfig(BaseModel):
    """Direct Streamable-HTTP MCP company risk verification (Tianyancha / Qichacha)."""

    enabled: bool = False
    provider: Literal["none", "tianyancha_mcp", "qichacha_mcp", "custom_mcp"] = "tianyancha_mcp"
    mcp_url: str = ""
    api_key_env: str = "TYC_MCP_API_KEY"
    cache_days: int = Field(default=30, ge=1, le=365)
    min_score_to_check: int = Field(default=60, ge=0, le=200)
    auto_reject_severe_risk: bool = True
    max_companies_per_run: int = Field(default=30, ge=1, le=200)


class UserConfig(BaseModel):
    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    preferences: PreferencesConfig = Field(default_factory=PreferencesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    cloud_relay: CloudRelayConfig = Field(default_factory=CloudRelayConfig)
    company_check: CompanyCheckConfig = Field(default_factory=CompanyCheckConfig)


def get_code_root() -> Path:
    override = os.getenv("JOB_AUTO_CODE_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        exe_parent = Path(sys.executable).resolve().parent
        # When bundled inside Electron resources/backend/job-agent-backend.exe, resources/ holds prompts & extensions
        if (exe_parent.parent / "prompts").is_dir():
            return exe_parent.parent
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return exe_parent
    return Path(__file__).resolve().parents[2]


def get_project_root() -> Path:
    override = os.getenv("JOB_AUTO_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path.cwd().resolve()
    return Path(__file__).resolve().parents[2]


def load_user_config(config_path: Path | None = None) -> UserConfig:
    """Load private config/user_config.yaml, falling back to example defaults."""
    root = get_project_root()
    code_root = get_code_root()
    candidates = (
        [config_path]
        if config_path is not None
        else [
            root / "config" / "user_config.yaml",
            root / "config" / "user_config.example.yaml",
            code_root / "config" / "user_config.example.yaml",
        ]
    )
    for path in candidates:
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return UserConfig.model_validate(raw)
    return UserConfig()

"""Safe GUI settings store, .env updater, resume importer, and schedule controller."""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values, load_dotenv
from pypdf import PdfReader

from .config import UserConfig, get_project_root, load_user_config
from .db import Database
from .master import MasterBullet, MasterEducation, MasterExperience, MasterProfile, QABank
from .presets import (
    EMAIL_PROVIDER_PRESETS,
    LLM_PROVIDER_PRESETS,
    PUSH_PROVIDER_PRESETS,
    resolve_email_preset,
    resolve_llm_preset,
    resolve_push_preset,
)

SCHEDULE_TASK_NAME = "JobAutoDailyEmail1600"
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _mask_secret(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if len(text) <= 6:
        return "****"
    return f"{text[:3]}...{text[-4:]}"


def _clean_env_val(raw: str) -> str:
    return str(raw or "").replace("\r", "").replace("\n", "").strip()


def upsert_env_vars(env_path: Path, updates: dict[str, str]) -> list[str]:
    """Safely update/append keys in .env while preserving unrelated lines and syncing os.environ."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    clean_updates = {
        k.strip(): _clean_env_val(v)
        for k, v in updates.items()
        if k.strip() and _clean_env_val(v) != ""
    }
    if not clean_updates:
        return []

    existing_lines = (
        env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    )
    remaining = dict(clean_updates)
    new_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        replaced = False
        for key in list(remaining):
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={remaining.pop(key)}")
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for key, val in remaining.items():
        new_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    for key, val in clean_updates.items():
        os.environ[key] = val
    return list(clean_updates.keys())


def _split_csv_tokens(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw or "").strip()
    if not text:
        return []
    return [tok.strip() for tok in re.split(r"[,，、;\n]+", text) if tok.strip()]


def _read_env_map(root: Path) -> dict[str, str]:
    env_path = root / ".env"
    load_dotenv(env_path, override=False)
    merged: dict[str, str] = {}
    if env_path.is_file():
        for k, v in dotenv_values(env_path).items():
            if v is not None:
                merged[k] = str(v)
    for k, v in os.environ.items():
        if v:
            merged.setdefault(k, v)
    return merged


def query_daily_email_schedule() -> dict[str, Any]:
    """Query daily digest email schedule status cleanly without shell injection."""
    if os.name != "nt":
        return {
            "supported": False,
            "enabled": False,
            "send_time": "16:00",
            "timezone": "Asia/Shanghai (UTC+8)",
            "note": "非 Windows 系统可通过 crontab 配置：0 16 * * * job-agent daily-cycle --skip-sync --skip-edge --skip-prefilter --skip-llm --send-email",
        }
    try:
        ps_cmd = (
            f"$t = Get-ScheduledTask -TaskName '{SCHEDULE_TASK_NAME}' -ErrorAction SilentlyContinue; "
            "if ($null -eq $t) { Write-Output '{\"enabled\":false}' } "
            "else { "
            "$tr = $t.Triggers | Select-Object -First 1; "
            "$sb = if ($tr.StartBoundary) { $tr.StartBoundary } else { '' }; "
            "$info = Get-ScheduledTaskInfo -TaskName $t.TaskName -ErrorAction SilentlyContinue; "
            "Write-Output (@{enabled=($t.State -ne 'Disabled');state=[string]$t.State;start_boundary=$sb;next_run=([string]$info.NextRunTime)} | ConvertTo-Json -Compress) "
            "}"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        raw = (proc.stdout or "").strip()
        data = json.loads(raw) if raw.startswith("{") else {}
        sb = str(data.get("start_boundary") or "")
        m = re.search(r"T(\d{2}:\d{2})", sb)
        send_time = m.group(1) if m else "16:00"
        return {
            "supported": True,
            "task_name": SCHEDULE_TASK_NAME,
            "enabled": bool(data.get("enabled", False)),
            "state": data.get("state", "NotRegistered"),
            "send_time": send_time,
            "next_run": data.get("next_run", ""),
            "timezone": "China Standard Time (UTC+8 东八区)",
        }
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {
            "supported": True,
            "enabled": False,
            "send_time": "16:00",
            "timezone": "China Standard Time (UTC+8 东八区)",
            "error": str(exc),
        }


def configure_daily_email_schedule(
    *,
    enabled: bool,
    send_time: str = "16:00",
    root: Path | None = None,
) -> dict[str, Any]:
    """Enable/disable Windows Task Scheduler daily email trigger cleanly."""
    clean_time = (send_time or "16:00").strip()
    if not _TIME_RE.match(clean_time):
        raise ValueError(f"时间格式须为 HH:MM（例如 16:00），收到：{send_time!r}")
    resolved_root = (root or get_project_root()).resolve()

    if os.name != "nt":
        hh, mm = clean_time.split(":")
        return {
            "status": "unsupported_os",
            "enabled": False,
            "send_time": clean_time,
            "cron_hint": f"{int(mm)} {int(hh)} * * * cd {resolved_root} && .venv/bin/python -m job_agent.cli daily-cycle --skip-sync --skip-edge --skip-prefilter --skip-llm --send-email",
        }

    bat_path = resolved_root / "scripts" / "send_daily_email.bat"
    if enabled:
        ps_cmd = (
            f"$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c \"{bat_path}\"' -WorkingDirectory '{resolved_root}'; "
            f"$trigger = New-ScheduledTaskTrigger -Daily -At '{clean_time}'; "
            "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
            f"Register-ScheduledTask -TaskName '{SCHEDULE_TASK_NAME}' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null"
        )
    else:
        ps_cmd = f"Unregister-ScheduledTask -TaskName '{SCHEDULE_TASK_NAME}' -Confirm:$false -ErrorAction SilentlyContinue"

    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "修改计划任务失败")
    return {"status": "ok", **query_daily_email_schedule()}


def _load_root_config(resolved_root: Path) -> UserConfig:
    local_cfg = resolved_root / "config" / "user_config.yaml"
    if local_cfg.is_file():
        return load_user_config(config_path=local_cfg)
    ex_cfg = resolved_root / "config" / "user_config.example.yaml"
    if ex_cfg.is_file():
        return load_user_config(config_path=ex_cfg)
    return load_user_config()


def read_safe_app_settings(
    *,
    root: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return non-secret settings view + presets + master resume status for the UI."""
    resolved_root = (root or get_project_root()).resolve()
    resolved_db = (db_path or (resolved_root / "data" / "job_agent.db")).resolve()
    cfg = _load_root_config(resolved_root)
    env_map = _read_env_map(resolved_root)

    llm_preset = resolve_llm_preset(cfg.llm.primary_provider)
    llm_env_name = (cfg.llm.api_key_env or llm_preset.get("api_key_env") or "LLM_API_KEY").strip()
    llm_key_raw = env_map.get(llm_env_name, "")

    fb_env_name = (cfg.llm.fallback_api_key_env or "FALLBACK_LLM_API_KEY").strip()
    fb_key_raw = env_map.get(fb_env_name, "")

    smtp_host_val = (env_map.get(cfg.notifications.smtp_host_env, "") or cfg.notifications.smtp_host).strip()
    smtp_port_val = (
        env_map.get(cfg.notifications.smtp_port_env, "").strip()
        or (str(cfg.notifications.smtp_port) if cfg.notifications.smtp_port else "")
        or str(resolve_email_preset(cfg.notifications.email_preset).get("port") or 465)
    )
    smtp_user_val = env_map.get(cfg.notifications.smtp_user_env, "").strip()
    smtp_pass_raw = env_map.get(cfg.notifications.smtp_pass_env, "")
    push_env_name = (cfg.notifications.push_webhook_env or "PUSH_WEBHOOK_URL").strip()
    push_url_raw = env_map.get(push_env_name, "")
    relay_env_name = (cfg.cloud_relay.relay_secret_env or "CLOUD_RELAY_SECRET").strip()
    relay_secret_raw = env_map.get(relay_env_name, "")

    master_summary: dict[str, Any] = {"loaded": False, "version_tag": None, "bullets": 0}
    if resolved_db.is_file():
        db = Database(resolved_db)
        with db.connect() as conn:
            row = conn.execute(
                "SELECT version_tag, profile_json, created_at FROM master_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                bullets = 0
                school = ""
                try:
                    prof = json.loads(row["profile_json"] or "{}")
                    school = str((prof.get("education") or {}).get("school") or "")
                    for exp in prof.get("experiences") or []:
                        bullets += len(exp.get("bullets") or [])
                except json.JSONDecodeError:
                    pass
                master_summary = {
                    "loaded": True,
                    "version_tag": row["version_tag"],
                    "school": school,
                    "bullets": bullets,
                    "updated_at": row["created_at"],
                }

    return {
        "status": "ok",
        "llm_presets": list(LLM_PROVIDER_PRESETS.values()),
        "email_presets": list(EMAIL_PROVIDER_PRESETS.values()),
        "push_presets": list(PUSH_PROVIDER_PRESETS.values()),
        "llm": {
            "primary_provider": cfg.llm.primary_provider,
            "base_url": cfg.llm.base_url or llm_preset.get("base_url", ""),
            "default_model": cfg.llm.default_model,
            "reasoning_model": cfg.llm.reasoning_model,
            "api_key_env": llm_env_name,
            "api_key_set": bool(llm_key_raw),
            "api_key_masked": _mask_secret(llm_key_raw),
            "fallback_enabled": cfg.llm.fallback_enabled,
            "fallback_base_url": cfg.llm.fallback_base_url,
            "fallback_model": cfg.llm.fallback_model,
            "fallback_api_key_env": fb_env_name,
            "fallback_api_key_set": bool(fb_key_raw),
            "fallback_api_key_masked": _mask_secret(fb_key_raw),
        },
        "notifications": {
            "strategy": cfg.notifications.strategy,
            "desktop_notify_enabled": cfg.notifications.desktop_notify_enabled,
            "push_preset": cfg.notifications.push_preset,
            "push_webhook_env": push_env_name,
            "push_webhook_set": bool(push_url_raw),
            "push_webhook_masked": _mask_secret(push_url_raw),
            "provider": cfg.notifications.provider,
            "email_preset": cfg.notifications.email_preset,
            "email_to": cfg.notifications.email_to,
            "smtp_host": smtp_host_val,
            "smtp_port": int(smtp_port_val) if str(smtp_port_val).isdigit() else 465,
            "smtp_security": cfg.notifications.smtp_security,
            "smtp_user": smtp_user_val,
            "smtp_pass_set": bool(smtp_pass_raw),
            "smtp_pass_masked": _mask_secret(smtp_pass_raw),
        },
        "profile": {
            "resume_path": cfg.profile.resume_path,
            "graduation_year": cfg.profile.graduation_year,
            "degree": cfg.profile.degree,
            "major": cfg.profile.major,
            "target_roles": cfg.profile.target_roles,
        },
        "preferences": {
            "primary_cities": cfg.preferences.primary_cities,
            "secondary_cities": cfg.preferences.secondary_cities,
            "excluded_keywords": cfg.preferences.excluded_keywords,
        },
        "scoring": {
            "min_score_for_package": cfg.scoring.min_score_for_package,
            "daily_top_n": cfg.scoring.daily_top_n,
        },
        "master": master_summary,
        "schedule": query_daily_email_schedule(),
        "cloud_relay": {
            "enabled": cfg.cloud_relay.enabled,
            "provider": cfg.cloud_relay.provider,
            "endpoint_url": cfg.cloud_relay.endpoint_url,
            "pairing_id": cfg.cloud_relay.pairing_id,
            "relay_secret_env": relay_env_name,
            "relay_secret_set": bool(relay_secret_raw),
            "relay_secret_masked": _mask_secret(relay_secret_raw),
            "ttl_days": cfg.cloud_relay.ttl_days,
            "auto_fallback_to_email": cfg.cloud_relay.auto_fallback_to_email,
        },
    }


def save_app_settings(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate and persist GUI configuration into config/user_config.yaml and .env."""
    resolved_root = (root or get_project_root()).resolve()
    cfg_path = resolved_root / "config" / "user_config.yaml"
    if cfg_path.is_file():
        raw_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    else:
        ex = resolved_root / "config" / "user_config.example.yaml"
        raw_cfg = yaml.safe_load(ex.read_text(encoding="utf-8")) if ex.is_file() else {}
    if not isinstance(raw_cfg, dict):
        raw_cfg = {}

    env_updates: dict[str, str] = {}

    if "llm" in payload and isinstance(payload["llm"], dict):
        lin = payload["llm"]
        preset = resolve_llm_preset(lin.get("primary_provider"))
        sec = dict(raw_cfg.get("llm") or {})
        sec["primary_provider"] = str(preset["id"])
        sec["base_url"] = str(lin.get("base_url") if lin.get("base_url") is not None else preset.get("base_url", "")).strip()
        sec["default_model"] = str(lin.get("default_model") or preset.get("default_model") or "gemini-3.5-flash-lite").strip()
        sec["reasoning_model"] = str(lin.get("reasoning_model") or sec["default_model"]).strip()
        sec["lite_model"] = sec["default_model"]
        env_name = str(lin.get("api_key_env") or preset.get("api_key_env") or "LLM_API_KEY").strip()
        sec["api_key_env"] = env_name
        sec["fallback_enabled"] = bool(lin.get("fallback_enabled", False))
        sec["fallback_base_url"] = str(lin.get("fallback_base_url") or "").strip()
        sec["fallback_model"] = str(lin.get("fallback_model") or "").strip()
        sec["fallback_api_key_env"] = str(lin.get("fallback_api_key_env") or "FALLBACK_LLM_API_KEY").strip()
        raw_cfg["llm"] = sec

        if lin.get("api_key"):
            env_updates[env_name] = str(lin["api_key"]).strip()
        if sec["base_url"] and preset["mode"] != "gemini":
            env_updates["LLM_BASE_URL"] = sec["base_url"]
        if lin.get("fallback_api_key"):
            env_updates[sec["fallback_api_key_env"]] = str(lin["fallback_api_key"]).strip()

    if "notifications" in payload and isinstance(payload["notifications"], dict):
        nin = payload["notifications"]
        epreset = resolve_email_preset(nin.get("email_preset"))
        ppreset = resolve_push_preset(nin.get("push_preset"))
        sec = dict(raw_cfg.get("notifications") or {})
        strat = str(nin.get("strategy") or sec.get("strategy") or "app_first").strip().lower()
        if strat in {"app_first", "app_and_email", "app_only", "email_only"}:
            sec["strategy"] = strat
        if nin.get("desktop_notify_enabled") is not None:
            sec["desktop_notify_enabled"] = bool(nin.get("desktop_notify_enabled"))
        if nin.get("push_preset") is not None:
            sec["push_preset"] = str(ppreset["id"])
        push_env = str(sec.get("push_webhook_env") or "PUSH_WEBHOOK_URL")
        if nin.get("push_webhook_url"):
            env_updates[push_env] = str(nin["push_webhook_url"]).strip()

        provider_val = str(nin.get("provider") or sec.get("provider") or "email_smtp").strip()
        sec["provider"] = provider_val if provider_val in {"email_smtp", "webhook", "none"} else "email_smtp"
        if nin.get("email_preset") is not None:
            sec["email_preset"] = str(epreset["id"])
        if nin.get("email_to") is not None:
            sec["email_to"] = str(nin.get("email_to") or "").strip()
        if nin.get("smtp_host") is not None or "email_preset" in nin:
            smtp_host = str(nin.get("smtp_host") if nin.get("smtp_host") is not None else epreset.get("host", "")).strip()
            sec["smtp_host"] = smtp_host
            if smtp_host:
                env_updates[str(sec.get("smtp_host_env") or "SMTP_HOST")] = smtp_host
        if nin.get("smtp_port") is not None or "email_preset" in nin:
            smtp_port = int(nin.get("smtp_port") or epreset.get("port") or 465)
            sec["smtp_port"] = smtp_port
            env_updates[str(sec.get("smtp_port_env") or "SMTP_PORT")] = str(smtp_port)
        if nin.get("smtp_security") is not None or "email_preset" in nin:
            sec_mode = str(nin.get("smtp_security") or epreset.get("security") or "auto").strip().lower()
            sec["smtp_security"] = sec_mode if sec_mode in {"auto", "ssl", "starttls", "none"} else "auto"
        raw_cfg["notifications"] = sec

        user_env = str(sec.get("smtp_user_env") or "SMTP_USER")
        pass_env = str(sec.get("smtp_pass_env") or "SMTP_PASS")
        if nin.get("smtp_user"):
            env_updates[user_env] = str(nin["smtp_user"]).strip()
        if nin.get("smtp_pass"):
            env_updates[pass_env] = str(nin["smtp_pass"]).strip()

    if "profile" in payload and isinstance(payload["profile"], dict):
        pin = payload["profile"]
        sec = dict(raw_cfg.get("profile") or {})
        if pin.get("graduation_year"):
            sec["graduation_year"] = int(pin["graduation_year"])
        if pin.get("degree") is not None:
            sec["degree"] = str(pin["degree"]).strip() or "本科"
        if pin.get("major") is not None:
            sec["major"] = str(pin["major"]).strip()
        if pin.get("target_roles") is not None:
            sec["target_roles"] = _split_csv_tokens(pin["target_roles"])
        raw_cfg["profile"] = sec

    if "preferences" in payload and isinstance(payload["preferences"], dict):
        pref_in = payload["preferences"]
        sec = dict(raw_cfg.get("preferences") or {})
        if pref_in.get("primary_cities") is not None:
            sec["primary_cities"] = _split_csv_tokens(pref_in["primary_cities"])
        if pref_in.get("secondary_cities") is not None:
            sec["secondary_cities"] = _split_csv_tokens(pref_in["secondary_cities"])
        if pref_in.get("excluded_keywords") is not None:
            sec["excluded_keywords"] = _split_csv_tokens(pref_in["excluded_keywords"])
        raw_cfg["preferences"] = sec

    if "scoring" in payload and isinstance(payload["scoring"], dict):
        sin = payload["scoring"]
        sec = dict(raw_cfg.get("scoring") or {})
        if sin.get("min_score_for_package") is not None:
            sec["min_score_for_package"] = int(sin["min_score_for_package"])
        if sin.get("daily_top_n") is not None:
            sec["daily_top_n"] = int(sin["daily_top_n"])
        raw_cfg["scoring"] = sec

    if "cloud_relay" in payload and isinstance(payload["cloud_relay"], dict):
        rin = payload["cloud_relay"]
        sec = dict(raw_cfg.get("cloud_relay") or {})
        if rin.get("enabled") is not None:
            sec["enabled"] = bool(rin["enabled"])
        if rin.get("provider") in {"none", "cloudflare_worker", "custom_http"}:
            sec["provider"] = str(rin["provider"])
        if rin.get("endpoint_url") is not None:
            sec["endpoint_url"] = str(rin["endpoint_url"] or "").strip()
        if rin.get("pairing_id") is not None:
            sec["pairing_id"] = str(rin["pairing_id"] or "").strip()
        if rin.get("ttl_days") is not None:
            sec["ttl_days"] = max(1, min(30, int(rin["ttl_days"])))
        if rin.get("auto_fallback_to_email") is not None:
            sec["auto_fallback_to_email"] = bool(rin["auto_fallback_to_email"])
        sec["relay_secret_env"] = str(rin.get("relay_secret_env") or sec.get("relay_secret_env") or "CLOUD_RELAY_SECRET").strip()
        raw_cfg["cloud_relay"] = sec
        if rin.get("relay_secret"):
            env_updates[sec["relay_secret_env"]] = str(rin["relay_secret"]).strip()

    # Validate before writing disk so malformed config never breaks startup.
    validated = UserConfig.model_validate(raw_cfg)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump(raw_cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    updated_env = upsert_env_vars(resolved_root / ".env", env_updates)
    return {
        "status": "ok",
        "config_path": str(cfg_path),
        "updated_env_keys": updated_env,
        "primary_provider": validated.llm.primary_provider,
        "email_preset": validated.notifications.email_preset,
    }


def _extract_resume_text(raw_bytes: bytes, suffix: str) -> str:
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    return raw_bytes.decode("utf-8", errors="ignore").strip()


def _build_starter_master_from_text(text: str, cfg: UserConfig, *, version_tag: str) -> MasterProfile:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullets: list[MasterBullet] = []
    for idx, ln in enumerate(lines[:10], start=1):
        clean_ln = re.sub(r"^[-*•·\d.)\s]+", "", ln).strip()
        if len(clean_ln) < 6:
            continue
        bullets.append(
            MasterBullet(
                id=f"B{idx}",
                text=clean_ln[:240],
                tags=[cfg.profile.major or "通用"],
                facts=[clean_ln[:120]],
            )
        )
    if not bullets:
        bullets.append(
            MasterBullet(
                id="B1",
                text=f"{cfg.profile.graduation_year} 届{cfg.profile.degree}（{cfg.profile.major or '相关专业'}）求职背景简历",
                tags=["教育背景"],
                facts=[],
            )
        )

    return MasterProfile(
        version_tag=version_tag,
        education=MasterEducation(
            school="个人院校（可在简历模板继续完善）",
            major=cfg.profile.major or "未填写专业",
            degree=cfg.profile.degree or "本科",
            period=f"{cfg.profile.graduation_year - 4}.09 - {cfg.profile.graduation_year}.06",
            graduation_year=cfg.profile.graduation_year,
        ),
        certifications=list(cfg.profile.certifications),
        skills=[],
        experiences=[
            MasterExperience(
                id="EXP1",
                category="project",
                organization="个人导入简历摘要",
                role=" / ".join(cfg.profile.target_roles[:2]) or "应届生",
                period=str(cfg.profile.graduation_year),
                bullets=bullets,
            )
        ],
        proper_nouns_whitelist=[],
    )


def import_resume_artifact(
    *,
    filename: str = "resume.txt",
    content_text: str | None = None,
    content_base64: str | None = None,
    db_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Import a user's resume (.pdf/.md/.txt/.json) and initialize MasterProfile cleanly in UI."""
    resolved_root = (root or get_project_root()).resolve()
    resolved_db = (db_path or (resolved_root / "data" / "job_agent.db")).resolve()
    vault_dir = resolved_root / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename or "resume.txt").name
    suffix = Path(safe_name).suffix.lower() or ".txt"
    if content_base64:
        raw_bytes = base64.b64decode(content_base64.encode("ascii"))
    else:
        raw_bytes = (content_text or "").encode("utf-8")
    if not raw_bytes:
        raise ValueError("简历内容为空，请选择 PDF/TXT/MD/JSON 文件或粘贴简历正文。")

    saved_raw = vault_dir / f"uploaded_{safe_name}"
    saved_raw.write_bytes(raw_bytes)

    cfg = _load_root_config(resolved_root)
    db = Database(resolved_db)
    db.init_schema()

    if suffix == ".json":
        profile = MasterProfile.model_validate(json.loads(raw_bytes.decode("utf-8")))
        qa_bank = QABank(version_tag=profile.version_tag, items=[])
        extracted_chars = len(raw_bytes)
    else:
        extracted = _extract_resume_text(raw_bytes, suffix)
        if not extracted:
            raise ValueError("未能从文件中提取文字，请尝试文本版 PDF 或直接粘贴简历文本。")
        text_path = vault_dir / "resume_extracted_latest.txt"
        text_path.write_text(extracted, encoding="utf-8")
        stamp = datetime.now().strftime("ui-%Y%m%d-%H%M%S")
        profile = _build_starter_master_from_text(extracted, cfg, version_tag=stamp)
        qa_bank = QABank(version_tag=stamp, items=[])
        extracted_chars = len(extracted)

    master_id = db.upsert_master_version(
        version_tag=profile.version_tag,
        profile_json=profile.model_dump_json(),
        qa_bank_json=qa_bank.model_dump_json(),
    )

    cfg_path = resolved_root / "config" / "user_config.yaml"
    if cfg_path.is_file():
        raw_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw_cfg, dict):
            prof_sec = dict(raw_cfg.get("profile") or {})
            prof_sec["resume_path"] = str(saved_raw)
            raw_cfg["profile"] = prof_sec
            cfg_path.write_text(yaml.safe_dump(raw_cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return {
        "status": "ok",
        "master_id": master_id,
        "version_tag": profile.version_tag,
        "saved_path": str(saved_raw),
        "bullets_count": len(profile.all_bullet_ids()),
        "extracted_chars": extracted_chars,
    }

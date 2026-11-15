from __future__ import annotations

import json
import smtplib
from pathlib import Path
from typing import Any, Self

from fastapi.testclient import TestClient

from job_agent.config import LLMConfig, NotificationsConfig, UserConfig
from job_agent.db import Database
from job_agent.llm.openai_compat import (
    OpenAICompatibleProvider,
    build_llm_provider,
)
from job_agent.llm.openai_compat import (
    test_llm_connection as probe_llm_connection,
)
from job_agent.notifications import dispatch_notification
from job_agent.presets import resolve_email_preset, resolve_llm_preset, resolve_push_preset
from job_agent.settings_store import (
    import_resume_artifact,
    read_safe_app_settings,
    save_app_settings,
)
from job_agent.stage3.digest import send_email_digest
from job_agent.stage3.review_server import create_review_app


def test_presets_and_open_llm_routing(tmp_path: Path, monkeypatch) -> None:
    ds_preset = resolve_llm_preset("deepseek")
    assert ds_preset["mode"] == "openai_compat"
    assert "deepseek.com" in ds_preset["base_url"]

    ollama_preset = resolve_llm_preset("ollama")
    assert ollama_preset["requires_key"] is False

    # DeepSeek routing works via OpenAICompatibleProvider with its own env var
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek-secret-9999")
    cfg_ds = UserConfig(
        llm=LLMConfig(
            primary_provider="deepseek",
            base_url=ds_preset["base_url"],
            default_model="deepseek-chat",
            api_key_env="DEEPSEEK_API_KEY",
        )
    )
    provider_ds = build_llm_provider(cfg_ds)
    assert isinstance(provider_ds, OpenAICompatibleProvider)
    assert provider_ds._resolve_api_key() == "sk-test-deepseek-secret-9999"

    # Ollama local provider works even WITHOUT any API key configured
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    cfg_ollama = UserConfig(
        llm=LLMConfig(
            primary_provider="ollama",
            base_url="http://127.0.0.1:11434/v1",
            default_model="qwen2.5:7b",
            api_key_env="OLLAMA_API_KEY",
        )
    )
    provider_ollama = build_llm_provider(cfg_ollama)
    assert isinstance(provider_ollama, OpenAICompatibleProvider)
    assert provider_ollama.requires_key is False
    assert provider_ollama._resolve_api_key() == "local-no-key"

    # Live LLM connectivity probe mock
    class _FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": '{"ok": true, "pong": "ready"}'}}]}

    def _fake_client_post(self: Any, url: str, **kwargs: Any) -> _FakeResp:
        assert url.endswith("/chat/completions")
        return _FakeResp()

    monkeypatch.setattr("httpx.Client.post", _fake_client_post)
    probe = probe_llm_connection(cfg_ds, project_root=tmp_path)
    assert probe["ok"] is True
    assert probe["reply"] == {"ok": True, "pong": "ready"}


def test_open_email_presets_and_smtp_modes(monkeypatch) -> None:
    preset_gmail = resolve_email_preset("gmail")
    assert preset_gmail["security"] == "starttls"
    assert preset_gmail["port"] == 587

    sent_records: list[dict[str, Any]] = []

    class _FakeSMTPSSL:
        def __init__(self, host: str, port: int, timeout: int = 20) -> None:
            sent_records.append({"mode": "ssl", "host": host, "port": port})

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            sent_records[-1]["user"] = user

        def send_message(self, msg: Any, from_addr: str | None = None, to_addrs: list[str] | None = None) -> None:
            sent_records[-1]["to"] = msg["To"]

    class _FakeSMTPStartTLS:
        def __init__(self, host: str, port: int, timeout: int = 20) -> None:
            sent_records.append({"mode": "starttls", "host": host, "port": port, "tls": False})

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def ehlo(self) -> None:
            return None

        def starttls(self) -> None:
            sent_records[-1]["tls"] = True

        def login(self, user: str, password: str) -> None:
            sent_records[-1]["user"] = user

        def send_message(self, msg: Any, from_addr: str | None = None, to_addrs: list[str] | None = None) -> None:
            sent_records[-1]["to"] = msg["To"]

    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTPSSL)
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTPStartTLS)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASS", "app-secret-pass")

    # Disabled email provider returns disabled cleanly
    disabled_cfg = UserConfig(notifications=NotificationsConfig(provider="none"))
    assert send_email_digest(disabled_cfg, subject="x", body_text="y")["status"] == "disabled"

    # 163 Mail via config host/port SSL + multiple recipients
    cfg_163 = UserConfig(
        notifications=NotificationsConfig(
            provider="email_smtp",
            email_preset="163",
            email_to="a@example.com, b@example.com",
            smtp_host="smtp.163.com",
            smtp_port=465,
            smtp_security="ssl",
        )
    )
    res_163 = send_email_digest(cfg_163, subject="Test 163", body_text="Hello")
    assert res_163["status"] == "sent"
    assert sent_records[-1]["mode"] == "ssl"
    assert sent_records[-1]["host"] == "smtp.163.com"
    assert sent_records[-1]["to"] == "a@example.com, b@example.com"

    # Gmail via STARTTLS on 587
    cfg_gmail = UserConfig(
        notifications=NotificationsConfig(
            provider="email_smtp",
            email_preset="gmail",
            email_to="target@gmail.com",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_security="starttls",
        )
    )
    res_gmail = send_email_digest(cfg_gmail, subject="Test Gmail", body_text="Hello")
    assert res_gmail["status"] == "sent"
    assert sent_records[-1]["mode"] == "starttls"
    assert sent_records[-1]["tls"] is True


def test_settings_store_masking_resume_import_and_api(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".env").write_text("# existing comment\nKEEP_ME=123\n", encoding="utf-8")

    # Isolate tests from host Task Scheduler & user env vars
    monkeypatch.setattr(
        "job_agent.settings_store.query_daily_email_schedule",
        lambda: {"supported": True, "enabled": False, "send_time": "16:00", "timezone": "UTC+8"},
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)

    db_path = tmp_path / "data" / "job_agent.db"
    Database(db_path).init_schema()

    save_res = save_app_settings(
        {
            "llm": {
                "primary_provider": "deepseek",
                "default_model": "deepseek-chat",
                "api_key": "sk-secret-value-abcdef1234",
            },
            "notifications": {
                "provider": "email_smtp",
                "email_preset": "163",
                "email_to": "recv@163.com",
                "smtp_host": "smtp.163.com",
                "smtp_port": 465,
                "smtp_security": "ssl",
                "smtp_user": "sender@163.com",
                "smtp_pass": "mail-secret-xyz987",
            },
            "profile": {
                "graduation_year": 2027,
                "degree": "本科",
                "major": "财务管理",
                "target_roles": "财务管培生, 审计助理",
            },
            "preferences": {
                "primary_cities": "成都, 重庆",
                "secondary_cities": "西安",
                "excluded_keywords": "销售, 电销",
            },
            "scoring": {"min_score_for_package": 78, "daily_top_n": 30},
        },
        root=tmp_path,
    )
    assert save_res["status"] == "ok"

    # Untouched .env lines stay intact
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "KEEP_ME=123" in env_text
    assert "DEEPSEEK_API_KEY=sk-secret-value-abcdef1234" in env_text

    # Safe reader MUST mask raw secrets!
    safe = read_safe_app_settings(root=tmp_path, db_path=db_path)
    safe_json = json.dumps(safe, ensure_ascii=False)
    assert "sk-secret-value-abcdef1234" not in safe_json
    assert "mail-secret-xyz987" not in safe_json
    assert safe["llm"]["api_key_set"] is True
    assert safe["llm"]["primary_provider"] == "deepseek"
    assert safe["notifications"]["smtp_pass_set"] is True
    assert safe["profile"]["major"] == "财务管理"

    # Resume text import populates active master_versions row
    imp = import_resume_artifact(
        filename="my_resume.md",
        content_text="# 个人简历\n- 某大学 会计学 本科 2027届\n- 参与企业年度审计底稿核对与银企对账项目\n- 熟练掌握 Excel 数据透视与财务建模",
        db_path=db_path,
        root=tmp_path,
    )
    assert imp["status"] == "ok"
    assert imp["bullets_count"] >= 2

    # FastAPI endpoints respect JOB_AUTO_ROOT and return masked settings
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    app = create_review_app(db_path=db_path, output_root=tmp_path / "output")
    client = TestClient(app)

    r_get = client.get("/api/system/settings")
    assert r_get.status_code == 200
    body = r_get.json()
    assert body["master"]["loaded"] is True
    assert "sk-secret-value-abcdef1234" not in r_get.text

    r_imp = client.post(
        "/api/system/import-resume",
        json={"filename": "pasted.txt", "content_text": "参与财务报表分析与资金预测项目，输出月度现金流周报"},
    )
    assert r_imp.status_code == 200
    assert r_imp.json()["bullets_count"] >= 1


def test_app_first_notifications_mobile_push_and_email_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "data" / "job_agent.db"
    db = Database(db_path)
    db.init_schema()

    assert resolve_push_preset("bark")["id"] == "bark"

    # Mock email + mobile push transport
    email_calls: list[str] = []
    push_calls: list[str] = []

    def _fake_send_email(cfg: UserConfig, *, subject: str, body_text: str, html_body: str | None = None) -> dict[str, Any]:
        email_calls.append(subject)
        return {"status": "sent", "email_to": cfg.notifications.email_to or "u@example.com"}

    class _OkPushResp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

    def _fake_push_post(self: Any, url: str, **kwargs: Any) -> _OkPushResp:
        push_calls.append(url)
        return _OkPushResp()

    monkeypatch.setattr("job_agent.notifications.send_email_digest", _fake_send_email)
    monkeypatch.setattr("httpx.Client.post", _fake_push_post)

    # 1) Default strategy ('app_first'): delivers App inbox + desktop toast, SKIPS email cleanly!
    cfg_app = UserConfig(
        notifications=NotificationsConfig(
            strategy="app_first",
            desktop_notify_enabled=True,
            push_preset="none",
            email_to="backup@example.com",
        )
    )
    res1 = dispatch_notification(
        db,
        cfg_app,
        title="今日新增 3 个高分岗位",
        body="请直接在 App 内挑选",
        project_root=tmp_path,
    )
    assert res1["app_notified"] is True
    assert "app_inbox" in res1["delivered_channels"]
    assert res1["email"]["status"] == "skipped_app_notified"
    assert email_calls == []

    # 2) App + Bark mobile push without needing email at all
    monkeypatch.setenv("PUSH_WEBHOOK_URL", "https://api.day.app/demo-secret-key")
    cfg_mobile = UserConfig(
        notifications=NotificationsConfig(
            strategy="app_first",
            desktop_notify_enabled=True,
            push_preset="bark",
        )
    )
    res2 = dispatch_notification(
        db,
        cfg_mobile,
        title="手机提醒测试",
        body="已发现新财务管培岗",
        project_root=tmp_path,
    )
    assert res2["mobile_push"]["status"] == "sent"
    assert any(u.startswith("https://api.day.app/demo-secret-key") for u in push_calls)
    assert email_calls == []

    # 3) Fallback check: when desktop notify is disabled & no mobile push, 'app_first' falls back to Email SMTP!
    cfg_fallback = UserConfig(
        notifications=NotificationsConfig(
            strategy="app_first",
            desktop_notify_enabled=False,
            push_preset="none",
            email_to="fallback@example.com",
        )
    )
    res3 = dispatch_notification(
        db,
        cfg_fallback,
        title="兜底邮件提醒",
        body="App 弹窗已关闭，自动通过邮件送达",
        project_root=tmp_path,
    )
    assert res3["email"]["status"] == "sent"
    assert len(email_calls) == 1

    # 4) FastAPI notification inbox & mark-read endpoints
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "job_agent.settings_store.query_daily_email_schedule",
        lambda: {"supported": True, "enabled": False, "send_time": "16:00", "timezone": "UTC+8"},
    )
    app = create_review_app(db_path=db_path, output_root=tmp_path / "output")
    client = TestClient(app)

    r_list = client.get("/api/notifications")
    assert r_list.status_code == 200
    assert r_list.json()["unread_count"] == 2

    r_test = client.post("/api/notifications/test")
    assert r_test.status_code == 200
    assert r_test.json()["app_notified"] is True

    r_read = client.post("/api/notifications/read", json={"ids": None})
    assert r_read.status_code == 200
    assert r_read.json()["unread_count"] == 0


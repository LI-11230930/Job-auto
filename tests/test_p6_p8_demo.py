"""Tests for P6-P8 Demo features: Scheme I UI, Lazy CLI, Zero-Config Demo Seed, and Pluggable E2EE Cloud Relay."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient

from job_agent.cli import main as cli_main
from job_agent.cloud_relay import (
    HttpCloudRelayClient,
    LocalLoopbackRelayStub,
    build_relay_client,
    open_payload,
    run_relay_sync_preview,
    seal_payload,
)
from job_agent.config import CloudRelayConfig, UserConfig
from job_agent.settings_store import read_safe_app_settings, save_app_settings
from job_agent.stage3.review_server import create_review_app


def test_cloud_relay_aes_gcm_roundtrip_and_tamper_detection() -> None:
    sample = {
        "generated_at": "2026-11-15T20:00:00Z",
        "items": [
            {"id": 1, "company": "晋商银行（示例企业）", "title": "总行财务会计管培生", "score": 94},
            {"id": 2, "company": "立信审计团队", "title": "年报审计助理", "score": 91},
        ],
    }
    envelope = seal_payload(sample, "super-secret-passphrase-123", pairing_id="pair-test-01")
    assert envelope["alg"] == "AES-256-GCM"
    assert envelope["pairing_id"] == "pair-test-01"
    assert "晋商银行" not in envelope["ciphertext"]

    decrypted = open_payload(envelope, "super-secret-passphrase-123")
    assert decrypted == sample

    # Wrong passphrase must fail authentication tag check
    with pytest.raises((InvalidTag, ValueError)):
        open_payload(envelope, "wrong-passphrase")

    # Tampered ciphertext must fail authentication tag check
    tampered = dict(envelope)
    first_char = "B" if envelope["ciphertext"].startswith("A") else "A"
    tampered["ciphertext"] = first_char + envelope["ciphertext"][1:]
    with pytest.raises((InvalidTag, ValueError)):
        open_payload(tampered, "super-secret-passphrase-123")


def test_cloud_relay_stub_and_adapter_factory(tmp_path: Path) -> None:
    stub = LocalLoopbackRelayStub(tmp_path / "stub")
    env = seal_payload({"items": [{"id": 10}]}, "demo-key", pairing_id="pair-stub")
    push_res = stub.push_batch(env)
    assert push_res["status"] == "stored_locally"
    assert push_res["mode"] == "local_stub"

    pulled = stub.pull_batch("pair-stub")
    assert pulled["envelope"] == env

    ack_env = seal_payload({"actions": [{"id": 10, "decision": "approve"}]}, "demo-key", pairing_id="pair-stub")
    stub.ack_actions(ack_env)
    actions_pulled = stub.pull_actions("pair-stub")
    assert actions_pulled["envelope"] == ack_env

    # Factory picks local stub when server is deferred / unconfigured
    cfg_none = CloudRelayConfig(enabled=False, provider="none", endpoint_url="")
    assert isinstance(build_relay_client(cfg_none, project_root=tmp_path), LocalLoopbackRelayStub)

    # Factory picks HTTP adapter once endpoint URL & provider are configured
    cfg_http = CloudRelayConfig(
        enabled=True,
        provider="custom_http",
        endpoint_url="https://relay.example.com/v1",
        pairing_id="pair-live",
    )
    client = build_relay_client(cfg_http, project_root=tmp_path)
    assert isinstance(client, HttpCloudRelayClient)
    assert client.endpoint_url == "https://relay.example.com/v1"

    preview = run_relay_sync_preview(
        UserConfig(cloud_relay=cfg_none),
        jobs_summary=[{"id": 1, "company": "Demo Co", "score": 92}],
        project_root=tmp_path,
    )
    assert preview["status"] == "ok"
    assert preview["mode"] == "local_stub"
    assert preview["roundtrip_verified"] is True
    assert preview["plaintext_count"] == 1


def test_review_app_demo_seed_relay_preview_and_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setenv("JOB_AUTO_CODE_ROOT", str(Path(__file__).resolve().parents[1] / "Job-auto"))

    db_path = tmp_path / "data" / "job_agent.db"
    output_root = tmp_path / "output"
    app = create_review_app(db_path=db_path, output_root=output_root)
    client = TestClient(app)

    # Initial relay status reports local_stub mode
    r_status = client.get("/api/relay/status")
    assert r_status.status_code == 200
    assert r_status.json()["mode"] == "local_stub"
    assert r_status.json()["fallback_to_email"] is True

    # Zero-config Demo Seeder populates 3 packages, PDFs & notifications
    seed_resp = client.post("/api/system/seed-demo")
    assert seed_resp.status_code == 200
    seed_data = seed_resp.json()
    assert seed_data["status"] == "ok"
    assert seed_data["packages_created"] == 3
    assert seed_data["master_version"] == "v1.0-demo"

    pkgs_resp = client.get("/api/packages")
    assert pkgs_resp.status_code == 200
    pkgs = pkgs_resp.json()["packages"]
    assert len(pkgs) == 3

    # Generated demo PDFs are served cleanly
    pdf_resp = client.get(f"/api/packages/{pkgs[0]['package_id']}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")

    # Relay preview encrypts the 3 seeded jobs & passes local decryption verification
    preview_resp = client.post("/api/relay/sync-preview")
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["status"] == "ok"
    assert preview["plaintext_count"] == 3
    assert preview["roundtrip_verified"] is True

    # Settings roundtrip masks cloud_relay secret cleanly
    saved = save_app_settings(
        {
            "cloud_relay": {
                "enabled": False,
                "provider": "custom_http",
                "endpoint_url": "https://relay.demo.local",
                "pairing_id": "pair-demo-99",
                "ttl_days": 14,
                "auto_fallback_to_email": True,
                "relay_secret": "SecretRelayKey98765",
            }
        },
        root=tmp_path,
    )
    assert "CLOUD_RELAY_SECRET" in saved["updated_env_keys"]

    monkeypatch.setenv("CLOUD_RELAY_SECRET", "SecretRelayKey98765")
    safe = read_safe_app_settings(root=tmp_path, db_path=db_path)
    cr = safe["cloud_relay"]
    assert cr["provider"] == "custom_http"
    assert cr["endpoint_url"] == "https://relay.demo.local"
    assert cr["pairing_id"] == "pair-demo-99"
    assert cr["ttl_days"] == 14
    assert cr["relay_secret_set"] is True
    assert "SecretRelayKey98765" not in cr["relay_secret_masked"]


def test_scheme_i_ui_tokens_zero_telemetry_and_js_syntax(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    app = create_review_app(db_path=tmp_path / "data" / "job_agent.db", output_root=tmp_path / "output")
    client = TestClient(app)

    html = client.get("/review").text
    assert "#2e1065" in html.lower()
    assert "#7c3aed" in html.lower()
    assert "零第三方统计" in html
    assert "一键载入示例体验数据" in html
    assert "ctrl+k" in html.lower()
    # Six independent top-level pages inside App; Progress page must NOT be in App Slim Rail
    assert 'href="/progress"' not in html
    for page_id in ("page-review", "page-inbox", "page-queue", "page-insights", "page-data", "page-settings"):
        assert f'id="{page_id}"' in html
    assert "msg-row" in html
    assert "queue-flat-card" in html
    assert "kanban-grid" in html
    assert 'id="cfgNav"' in html
    assert "acc-card" in html
    # Strictly no third-party telemetry hosts embedded
    lower_html = html.lower()
    for blocked in ("google-analytics", "googletagmanager", "sentry.io", "mixpanel", "posthog", "segment.com"):
        assert blocked not in lower_html

    m = re.search(r"<script>(.*?)</script>", html, flags=re.DOTALL)
    assert m is not None
    node_bin = shutil.which("node")
    if node_bin:
        js_file = tmp_path / "workbench_check.js"
        js_file.write_text(m.group(1), encoding="utf-8")
        proc = subprocess.run([node_bin, "--check", str(js_file)], check=False, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr


def test_cli_doctor_works_with_lazy_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    exit_code = cli_main(["--db", str(tmp_path / "data" / "job_agent.db"), "doctor"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "master_loaded" in out

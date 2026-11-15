"""Release readiness tests for v1.8.0: E2EE cloud relay loop, WebCrypto interop, calendar view, autofill bundle & packaging metadata."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from job_agent import __version__ as pkg_version
from job_agent.cloud_relay import (
    open_payload,
    pull_and_apply_relay_actions,
    push_packages_to_relay,
    seal_payload,
)
from job_agent.config import CloudRelayConfig, UserConfig
from job_agent.db import Database
from job_agent.demo_seed import seed_demo_workspace
from job_agent.relay_mobile_ui import render_relay_mobile_html
from job_agent.stage3.review_server import create_review_app
from job_agent.stage5.daily_cycle import run_daily_cycle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_version_alignment_and_release_workflow_contracts() -> None:
    root = _repo_root()
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    py_ver = pyproject["project"]["version"]
    desktop_pkg = json.loads((root / "desktop" / "package.json").read_text(encoding="utf-8"))
    ext_manifest = json.loads(
        (root / "extensions" / "job_auto_collector" / "manifest.json").read_text(encoding="utf-8")
    )

    assert pkg_version == "1.8.0"
    assert py_ver == "1.8.0"
    assert desktop_pkg["version"] == "1.8.0"
    assert ext_manifest["version"] == "1.3.0"

    workflow = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "pytest -v" in workflow
    assert "ruff check" in workflow
    assert "electron-builder --win portable nsis" in workflow
    assert "SHA256SUMS.txt" in workflow


def test_python_and_node_webcrypto_aes_gcm_cross_runtime_interop(tmp_path: Path) -> None:
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js not installed")

    secret = "cross-runtime-relay-secret-2026"
    pairing_id = "pair-interop-01"
    py_packet = {
        "schema": "job-auto.relay.batch.v1",
        "items": [
            {"package_id": 101, "company": "示例会计师事务所", "title": "审计助理", "score": 93}
        ],
    }
    py_env = seal_payload(py_packet, secret, pairing_id=pairing_id)
    in_path = tmp_path / "py_env.json"
    out_path = tmp_path / "js_actions_env.json"
    in_path.write_text(json.dumps(py_env, ensure_ascii=False), encoding="utf-8")

    js_script = tmp_path / "webcrypto_interop.mjs"
    js_script.write_text(
        f"""
import fs from 'node:fs';
import {{ webcrypto as crypto }} from 'node:crypto';

const b64uToBytes = (str) => {{
  const pad = '='.repeat((4 - (str.length % 4)) % 4);
  const b64 = (str + pad).replace(/-/g, '+').replace(/_/g, '/');
  return new Uint8Array(Buffer.from(b64, 'base64'));
}};
const bytesToB64u = (bytes) => Buffer.from(bytes).toString('base64').replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/g, '');

const secret = {json.dumps(secret)};
const pairingId = {json.dumps(pairing_id)};
const keyMaterial = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(secret));
const key = await crypto.subtle.importKey('raw', keyMaterial, {{ name: 'AES-GCM' }}, false, ['encrypt', 'decrypt']);

const incoming = JSON.parse(fs.readFileSync({json.dumps(str(in_path))}, 'utf8'));
const plainBuf = await crypto.subtle.decrypt(
  {{
    name: 'AES-GCM',
    iv: b64uToBytes(incoming.nonce),
    tagLength: 128,
    additionalData: new TextEncoder().encode(incoming.pairing_id),
  }},
  key,
  b64uToBytes(incoming.ciphertext),
);
const decoded = JSON.parse(new TextDecoder().decode(plainBuf));
if (decoded.items[0].package_id !== 101 || decoded.items[0].company !== '示例会计师事务所') {{
  throw new Error('Decrypted payload mismatch');
}}

const iv = crypto.getRandomValues(new Uint8Array(12));
const actions = {{ actions: [{{ package_id: 101, decision: 'approved', reason: 'webcrypto_ok' }}] }};
const ct = await crypto.subtle.encrypt(
  {{
    name: 'AES-GCM',
    iv,
    tagLength: 128,
    additionalData: new TextEncoder().encode(pairingId),
  }},
  key,
  new TextEncoder().encode(JSON.stringify(actions)),
);
const outgoing = {{
  v: 1,
  alg: 'AES-256-GCM',
  pairing_id: pairingId,
  nonce: bytesToB64u(iv),
  ciphertext: bytesToB64u(new Uint8Array(ct)),
}};
fs.writeFileSync({json.dumps(str(out_path))}, JSON.stringify(outgoing), 'utf8');
""",
        encoding="utf-8",
    )

    proc = subprocess.run([node_bin, str(js_script)], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    js_env = json.loads(out_path.read_text(encoding="utf-8"))
    opened = open_payload(js_env, secret)
    assert opened["actions"] == [{"package_id": 101, "decision": "approved", "reason": "webcrypto_ok"}]


def test_relay_bidirectional_api_and_autofill_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setenv("CLOUD_RELAY_SECRET", "e2ee-test-passphrase-99")

    app = create_review_app(db_path=tmp_path / "data" / "job_agent.db", output_root=tmp_path / "output")
    client = TestClient(app)

    assert client.post("/api/system/bootstrap").status_code == 200
    assert client.post("/api/system/seed-demo").status_code == 200
    assert client.post(
        "/api/system/settings",
        json={
            "cloud_relay": {
                "enabled": True,
                "provider": "none",
                "endpoint_url": "",
                "pairing_id": "pair-unit-test",
                "ttl_days": 7,
                "auto_fallback_to_email": True,
            }
        },
    ).status_code == 200

    # Import a tiny master resume so /api/autofill/bundle includes parsed profile fields
    imp = client.post(
        "/api/system/import-resume",
        json={
            "filename": "test_master.txt",
            "content_text": "林子轩\n山西科技大学 会计学 本科 2027届\n电话：13800138000\n邮箱：demo@example.com\n实习经历：太原某财务公司审计实习生（2026.07-2026.09）\n",
        },
    )
    assert imp.status_code == 200

    push_resp = client.post("/api/relay/push")
    assert push_resp.status_code == 200
    push_data = push_resp.json()
    assert push_data["status"] == "ok"
    assert push_data["pushed_count"] >= 2
    assert push_data["secret_configured"] is True

    # Pull ciphertext batch via stub HTTP route and decrypt locally
    stub_pull = client.get("/api/relay/stub/pull-batch", params={"pairing_id": "pair-unit-test"})
    assert stub_pull.status_code == 200
    batch_plain = open_payload(stub_pull.json()["envelope"], "e2ee-test-passphrase-99")
    items = batch_plain["items"]
    assert len(items) >= 2
    first_pid = items[0]["package_id"]
    second_pid = items[1]["package_id"]

    # Simulate mobile reviewer encrypting decisions back into stub ack-actions
    actions_env = seal_payload(
        {
            "actions": [
                {"package_id": first_pid, "decision": "approved", "reason": "go"},
                {"package_id": second_pid, "decision": "later", "reason": "wait"},
                {"package_id": 999999, "decision": "approved"},
            ]
        },
        "e2ee-test-passphrase-99",
        pairing_id="pair-unit-test",
    )
    ack = client.post("/api/relay/stub/ack-actions", json={"envelope": actions_env})
    assert ack.status_code == 200

    pull_resp = client.post("/api/relay/pull")
    assert pull_resp.status_code == 200
    pull_data = pull_resp.json()
    assert pull_data["applied_count"] == 2
    assert len(pull_data["skipped"]) == 1

    # Approved package must appear in /api/applications with deadline key exposed for Calendar view
    apps_resp = client.get("/api/applications")
    assert apps_resp.status_code == 200
    apps = apps_resp.json()["applications"]
    assert any(int(a["package_id"]) == first_pid and "deadline" in a for a in apps)

    # /api/autofill/bundle must return campus/intern profiles + package greeting
    bundle = client.get("/api/autofill/bundle").json()
    assert bundle["status"] == "ok"
    assert len(bundle["profiles"]) == 2
    assert len(bundle["packages"]) >= 1

    # /relay-mobile page renders cleanly and passes node --check
    mobile_html = client.get("/relay-mobile").text
    assert "AES-256-GCM" in mobile_html
    assert "btnPull" in mobile_html


def test_relay_push_network_failure_triggers_fallback_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setenv("CLOUD_RELAY_SECRET", "fallback-secret-01")
    db = Database(tmp_path / "data" / "job_agent.db")
    db.init_schema()
    seed_demo_workspace(db, output_root=tmp_path / "output")

    cfg = UserConfig(
        cloud_relay=CloudRelayConfig(
            enabled=True,
            provider="cloudflare_worker",
            endpoint_url="http://127.0.0.1:59999",
            pairing_id="pair-unreachable",
            auto_fallback_to_email=True,
        )
    )
    res = push_packages_to_relay(db, cfg, project_root=tmp_path)
    assert res["status"] == "fallback_email_triggered"
    assert res["fallback_to_email_ready"] is True
    notes = db.list_notifications(limit=5)
    assert any(n["category"] == "cloud_relay" for n in notes)


def test_daily_cycle_with_sync_relay_and_ui_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_AUTO_ROOT", str(tmp_path))
    monkeypatch.setenv("CLOUD_RELAY_SECRET", "cycle-secret-01")
    db = Database(tmp_path / "data" / "job_agent.db")
    db.init_schema()
    seed_demo_workspace(db, output_root=tmp_path / "output")

    cfg = UserConfig(
        cloud_relay=CloudRelayConfig(
            enabled=True,
            provider="none",
            endpoint_url="",
            pairing_id="pair-cycle",
        )
    )
    res = run_daily_cycle(
        db,
        cfg=cfg,
        output_root=tmp_path / "output",
        prompts_root=_repo_root() / "prompts",
        sync_sources=False,
        sync_edge=False,
        run_prefilter=False,
        run_llm=False,
        send_email=False,
        sync_relay=True,
        refresh_progress=False,
    )
    assert res["status"] == "ok"
    assert res["steps"]["relay_push"]["status"] == "ok"

    # Pull loop stays clean when no actions pending
    pull_empty = pull_and_apply_relay_actions(db, cfg, project_root=tmp_path)
    assert pull_empty["status"] == "empty"

    # Verify Calendar Month View + Relay buttons exist in workbench UI & JS compiles cleanly
    app = create_review_app(db_path=tmp_path / "data" / "job_agent.db", output_root=tmp_path / "output")
    review_html = TestClient(app).get("/review").text
    for marker in (
        "btnToggleCalendar",
        "renderCalendarMonthView",
        "cal-grid",
        "btnRelayPush",
        "btnRelayPull",
        'href="/relay-mobile"',
    ):
        assert marker in review_html

    node_bin = shutil.which("node")
    if node_bin:
        root = _repo_root()
        for js_path in (
            root / "deploy" / "cloudflare-worker" / "worker.js",
            root / "extensions" / "job_auto_collector" / "popup.js",
            root / "extensions" / "job_auto_collector" / "background.js",
        ):
            proc = subprocess.run(
                [node_bin, "--check", str(js_path)], check=False, capture_output=True, text=True
            )
            assert proc.returncode == 0, f"{js_path}: {proc.stderr}"

        mob_match = re.search(r"<script>(.*?)</script>", render_relay_mobile_html(), flags=re.DOTALL)
        assert mob_match is not None
        mob_js = tmp_path / "relay_mobile_check.js"
        mob_js.write_text(mob_match.group(1), encoding="utf-8")
        proc = subprocess.run(
            [node_bin, "--check", str(mob_js)], check=False, capture_output=True, text=True
        )
        assert proc.returncode == 0, proc.stderr

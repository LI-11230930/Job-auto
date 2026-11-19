"""Pluggable zero-knowledge encrypted cloud relay client & local stub (P8 deferred interface)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

from .config import CloudRelayConfig, UserConfig, get_project_root

if TYPE_CHECKING:
    from .db import Database


def _derive_aes_key(secret: str) -> bytes:
    """Derive a deterministic 256-bit AES key from a user-held pairing passphrase."""
    clean = (secret or "").strip()
    if not clean:
        raise ValueError("Encryption secret cannot be empty")
    return hashlib.sha256(clean.encode("utf-8")).digest()


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64u_decode(txt: str) -> bytes:
    pad = "=" * (-len(txt) % 4)
    return base64.urlsafe_b64decode(txt + pad)


def seal_payload(data: dict[str, Any], secret: str, *, pairing_id: str = "") -> dict[str, Any]:
    """Encrypt arbitrary JSON dict locally using AES-256-GCM before any network hop."""
    key = _derive_aes_key(secret)
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    aad = pairing_id.encode("utf-8") if pairing_id else None
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return {
        "v": 1,
        "alg": "AES-256-GCM",
        "pairing_id": pairing_id,
        "created_at": datetime.now(UTC).isoformat(),
        "nonce": _b64u_encode(nonce),
        "ciphertext": _b64u_encode(ciphertext),
    }


def open_payload(envelope: dict[str, Any], secret: str) -> dict[str, Any]:
    """Decrypt a zero-knowledge AES-256-GCM envelope back into structured JSON."""
    if envelope.get("alg") != "AES-256-GCM":
        raise ValueError(f"Unsupported relay cipher: {envelope.get('alg')}")
    key = _derive_aes_key(secret)
    nonce = _b64u_decode(str(envelope["nonce"]))
    ciphertext = _b64u_decode(str(envelope["ciphertext"]))
    pairing_id = str(envelope.get("pairing_id") or "")
    aad = pairing_id.encode("utf-8") if pairing_id else None
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    return json.loads(plaintext.decode("utf-8"))


class CloudRelayBackend(Protocol):
    """Protocol implemented by both remote HTTP relays (Workers/Docker) and the local offline stub."""

    mode: str

    def health(self) -> dict[str, Any]: ...

    def push_batch(self, envelope: dict[str, Any]) -> dict[str, Any]: ...

    def pull_batch(self, pairing_id: str) -> dict[str, Any]: ...

    def ack_actions(self, envelope: dict[str, Any]) -> dict[str, Any]: ...

    def pull_actions(self, pairing_id: str) -> dict[str, Any]: ...


class LocalLoopbackRelayStub:
    """Zero-cloud offline relay stub stored strictly inside local/relay_stub for demo & testing."""

    mode = "local_stub"

    def __init__(self, stub_dir: Path) -> None:
        self.stub_dir = stub_dir
        self.stub_dir.mkdir(parents=True, exist_ok=True)

    def health(self) -> dict[str, Any]:
        return {
            "status": "stub_ready",
            "mode": self.mode,
            "configured": False,
            "note": "尚未绑定云端服务器；当前使用本地加密回环演示模式（邮件兜底开关处于就绪态）。",
        }

    def push_batch(self, envelope: dict[str, Any]) -> dict[str, Any]:
        pid = str(envelope.get("pairing_id") or "default")
        target = self.stub_dir / f"batch_{pid}.json"
        target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "stored_locally", "mode": self.mode, "pairing_id": pid, "path": str(target)}

    def pull_batch(self, pairing_id: str) -> dict[str, Any]:
        target = self.stub_dir / f"batch_{pairing_id or 'default'}.json"
        if not target.is_file():
            return {"status": "empty", "mode": self.mode, "envelope": None}
        return {"status": "ok", "mode": self.mode, "envelope": json.loads(target.read_text(encoding="utf-8"))}

    def ack_actions(self, envelope: dict[str, Any]) -> dict[str, Any]:
        pid = str(envelope.get("pairing_id") or "default")
        target = self.stub_dir / f"actions_{pid}.json"
        target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "stored_locally", "mode": self.mode, "pairing_id": pid}

    def pull_actions(self, pairing_id: str) -> dict[str, Any]:
        target = self.stub_dir / f"actions_{pairing_id or 'default'}.json"
        if not target.is_file():
            return {"status": "empty", "mode": self.mode, "envelope": None}
        payload = json.loads(target.read_text(encoding="utf-8"))
        target.unlink(missing_ok=True)
        return {"status": "ok", "mode": self.mode, "envelope": payload}


class HttpCloudRelayClient:
    """Standard 4-route REST adapter targeting any future Cloudflare Worker or VPS Docker host."""

    mode = "remote_http"

    def __init__(self, endpoint_url: str, *, ttl_days: int = 7, timeout: float = 8.0) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.ttl_days = ttl_days
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(trust_env=False, timeout=self.timeout) as client:
                r = client.get(f"{self.endpoint_url}/health")
                r.raise_for_status()
                return {"status": "ok", "mode": self.mode, "configured": True, "remote": r.json()}
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return {"status": "unreachable", "mode": self.mode, "configured": True, "error": str(exc)}

    def push_batch(self, envelope: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(trust_env=False, timeout=self.timeout) as client:
            r = client.post(
                f"{self.endpoint_url}/push-batch",
                json={"ttl_days": self.ttl_days, "envelope": envelope},
            )
            r.raise_for_status()
            return r.json()

    def pull_batch(self, pairing_id: str) -> dict[str, Any]:
        with httpx.Client(trust_env=False, timeout=self.timeout) as client:
            r = client.get(f"{self.endpoint_url}/pull-batch", params={"pairing_id": pairing_id})
            r.raise_for_status()
            return r.json()

    def ack_actions(self, envelope: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(trust_env=False, timeout=self.timeout) as client:
            r = client.post(f"{self.endpoint_url}/ack-actions", json={"envelope": envelope})
            r.raise_for_status()
            return r.json()

    def pull_actions(self, pairing_id: str) -> dict[str, Any]:
        with httpx.Client(trust_env=False, timeout=self.timeout) as client:
            r = client.get(f"{self.endpoint_url}/pull-actions", params={"pairing_id": pairing_id})
            r.raise_for_status()
            return r.json()


def build_relay_client(
    relay_cfg: CloudRelayConfig,
    *,
    project_root: Path | None = None,
) -> CloudRelayBackend:
    """Return remote HTTP adapter if enabled + endpoint configured; otherwise return zero-network stub."""
    url = (relay_cfg.endpoint_url or "").strip()
    if relay_cfg.enabled and relay_cfg.provider != "none" and url.startswith(("https://", "http://")):
        return HttpCloudRelayClient(url, ttl_days=relay_cfg.ttl_days)
    root = project_root or get_project_root()
    return LocalLoopbackRelayStub(root / "local" / "relay_stub")


_RELAY_DECISION_ALIASES = {
    "approve": "approve",
    "approved": "approve",
    "later": "later",
    "reject": "reject",
    "rejected": "reject",
}


def _resolve_relay_credentials(
    cfg: UserConfig,
    *,
    project_root: Path | None = None,
) -> tuple[Path, str, str, bool]:
    """Load local .env if present and resolve pairing_id + local-only encryption passphrase."""
    root = project_root or get_project_root()
    load_dotenv(root / ".env", override=False)
    relay_cfg = cfg.cloud_relay
    pairing_id = (relay_cfg.pairing_id or "").strip() or "demo-pair-local"
    env_name = (relay_cfg.relay_secret_env or "CLOUD_RELAY_SECRET").strip() or "CLOUD_RELAY_SECRET"
    env_secret = os.environ.get(env_name, "").strip()
    secret = env_secret or "job-auto-local-demo-key"
    return root, pairing_id, secret, bool(env_secret)


def _format_relay_text(item: Any) -> str:
    if isinstance(item, dict):
        dim = str(item.get("dimension") or "").strip()
        ev = str(item.get("evidence") or item.get("text") or "").strip()
        if dim and ev:
            return f"[{dim}] {ev}"
        return ev or dim or json.dumps(item, ensure_ascii=False)
    return str(item or "")


def _serialize_package_for_relay(item: dict[str, Any]) -> dict[str, Any]:
    """Strip local filesystem paths and return compact mobile-friendly review summary."""
    return {
        "package_id": int(item["package_id"]),
        "job_id": int(item.get("job_id") or 0),
        "company": str(item.get("company") or ""),
        "title": str(item.get("title") or ""),
        "job_type": str(item.get("job_type") or ""),
        "cities": list(item.get("cities") or []),
        "deadline": str(item.get("deadline") or ""),
        "score": int(item.get("score") or 0),
        "reasons": [_format_relay_text(x) for x in (item.get("reasons") or [])][:4],
        "gaps": [_format_relay_text(x) for x in (item.get("gaps") or [])][:3],
        "greeting": str(item.get("greeting") or "")[:400],
        "url": str(item.get("url") or ""),
        "apply_channel": str(item.get("apply_channel") or ""),
        "source": str(item.get("source") or ""),
        "decision": str(item.get("decision") or "pending"),
    }


def run_relay_sync_preview(
    cfg: UserConfig,
    *,
    jobs_summary: list[dict[str, Any]],
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Generate an end-to-end encrypted preview envelope (uses local stub cleanly if cloud is unconfigured)."""
    root, pairing_id, secret, secret_configured = _resolve_relay_credentials(
        cfg, project_root=project_root
    )
    relay_cfg = cfg.cloud_relay

    packet = {
        "generated_at": datetime.now(UTC).isoformat(),
        "items": jobs_summary[:10],
    }
    envelope = seal_payload(packet, secret, pairing_id=pairing_id)
    client = build_relay_client(relay_cfg, project_root=root)

    try:
        push_res = client.push_batch(envelope)
        pull_res = client.pull_batch(pairing_id)
        roundtrip_ok = False
        if pull_res.get("envelope"):
            opened = open_payload(pull_res["envelope"], secret)
            roundtrip_ok = len(opened.get("items") or []) == len(packet["items"])
        return {
            "status": "ok",
            "mode": client.mode,
            "configured": client.mode == "remote_http",
            "secret_configured": secret_configured,
            "fallback_to_email_ready": bool(relay_cfg.auto_fallback_to_email),
            "pairing_id": pairing_id,
            "ciphertext_preview": str(envelope["ciphertext"])[:72] + "...",
            "plaintext_count": len(packet["items"]),
            "roundtrip_verified": roundtrip_ok,
            "push_result": push_res,
        }
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return {
            "status": "fallback_email_triggered",
            "mode": client.mode,
            "configured": True,
            "secret_configured": secret_configured,
            "fallback_to_email_ready": bool(relay_cfg.auto_fallback_to_email),
            "error": str(exc),
        }


def push_packages_to_relay(
    db: Database,
    cfg: UserConfig,
    *,
    limit: int = 20,
    decision_filter: str = "pending",
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Encrypt candidate review packages locally and push ciphertexts to the configured relay."""
    root, pairing_id, secret, secret_configured = _resolve_relay_credentials(
        cfg, project_root=project_root
    )
    relay_cfg = cfg.cloud_relay
    bounded_limit = max(1, min(int(limit), 50))
    packages = db.list_packages_for_review(
        decision_filter=decision_filter,
        job_type_filter="all",
        min_score=0,
        limit=bounded_limit * 3 if cfg.preferences.custom_filter.enabled else bounded_limit,
    )
    if cfg.preferences.custom_filter.enabled:
        from .filters import matches_custom_filter

        packages = [pkg for pkg in packages if matches_custom_filter(pkg, cfg)][:bounded_limit]
    items = [_serialize_package_for_relay(pkg) for pkg in packages]
    packet = {
        "schema": "job-auto.relay.batch.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "pairing_id": pairing_id,
        "count": len(items),
        "items": items,
    }
    envelope = seal_payload(packet, secret, pairing_id=pairing_id)
    client = build_relay_client(relay_cfg, project_root=root)

    try:
        push_res = client.push_batch(envelope)
        return {
            "status": "ok",
            "mode": client.mode,
            "configured": client.mode == "remote_http",
            "secret_configured": secret_configured,
            "pairing_id": pairing_id,
            "pushed_count": len(items),
            "decision_filter": decision_filter,
            "ttl_days": int(relay_cfg.ttl_days),
            "ciphertext_bytes": len(str(envelope.get("ciphertext") or "")),
            "push_result": push_res,
        }
    except (httpx.HTTPError, OSError, ValueError) as exc:
        if relay_cfg.auto_fallback_to_email:
            db.add_notification(
                title="云端加密中转推送失败，已触发本地邮件兜底提醒",
                body=f"目标：{relay_cfg.endpoint_url or client.mode}；原因：{exc}",
                level="warning",
                category="cloud_relay",
                action_tab="settings",
                payload={"error": str(exc)},
            )
        return {
            "status": "fallback_email_triggered",
            "mode": client.mode,
            "configured": client.mode == "remote_http",
            "secret_configured": secret_configured,
            "pairing_id": pairing_id,
            "pushed_count": 0,
            "fallback_to_email_ready": bool(relay_cfg.auto_fallback_to_email),
            "error": str(exc),
        }


def pull_and_apply_relay_actions(
    db: Database,
    cfg: UserConfig,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Pull encrypted mobile decisions from relay, decrypt locally, and write back to SQLite."""
    from .stage3.digest import resolve_delivery_mode

    root, pairing_id, secret, secret_configured = _resolve_relay_credentials(
        cfg, project_root=project_root
    )
    relay_cfg = cfg.cloud_relay
    client = build_relay_client(relay_cfg, project_root=root)

    try:
        res = client.pull_actions(pairing_id)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return {
            "status": "error",
            "mode": client.mode,
            "pairing_id": pairing_id,
            "secret_configured": secret_configured,
            "applied_count": 0,
            "error": str(exc),
        }

    raw_envelopes: list[dict[str, Any]] = []
    if isinstance(res.get("envelopes"), list):
        raw_envelopes.extend(e for e in res["envelopes"] if isinstance(e, dict))
    if isinstance(res.get("envelope"), dict):
        raw_envelopes.append(res["envelope"])

    if not raw_envelopes:
        return {
            "status": "empty",
            "mode": client.mode,
            "pairing_id": pairing_id,
            "secret_configured": secret_configured,
            "applied_count": 0,
            "applied": [],
            "skipped": [],
        }

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    decrypt_errors: list[str] = []

    for env in raw_envelopes:
        try:
            opened = open_payload(env, secret)
        except Exception as exc:  # noqa: BLE001 — surface invalid passphrase / tamper cleanly
            decrypt_errors.append(str(exc))
            continue

        actions = opened.get("actions")
        if not isinstance(actions, list):
            continue
        for entry in actions:
            if not isinstance(entry, dict):
                continue
            try:
                pkg_id = int(entry.get("package_id") or 0)
            except (TypeError, ValueError):
                skipped.append({"reason": "invalid_package_id", "entry": entry})
                continue
            raw_dec = str(entry.get("decision") or "").strip().lower()
            decision = _RELAY_DECISION_ALIASES.get(raw_dec, "")
            if pkg_id <= 0 or not decision:
                skipped.append({"package_id": pkg_id, "reason": "invalid_decision"})
                continue

            detail = db.get_package_detail(pkg_id)
            if not detail:
                skipped.append({"package_id": pkg_id, "reason": "package_not_found"})
                continue

            user_reason = str(entry.get("reason") or "").strip()
            tag = "[手机端零知识审阅]"
            reason = f"{tag} {user_reason}".strip() if user_reason else tag
            default_mode = resolve_delivery_mode(cfg, str(detail.get("apply_channel") or ""))
            dec_res = db.record_decision(
                package_id=pkg_id,
                decision=decision,
                reason=reason,
                default_mode=default_mode,
            )
            applied.append(
                {
                    "package_id": pkg_id,
                    "company": detail.get("company") or "",
                    "title": detail.get("title") or "",
                    "decision": decision,
                    "application_id": dec_res.get("application_id"),
                }
            )

    if applied:
        summary_lines = ", ".join(
            f"{a['company']}·{a['title']}({a['decision']})" for a in applied[:4]
        )
        db.add_notification(
            title=f"已同步 {len(applied)} 条手机端零知识审阅结果",
            body=summary_lines,
            level="info",
            category="cloud_relay",
            action_tab="queue",
            payload={"applied_count": len(applied)},
        )

    status = "ok"
    if decrypt_errors and not applied:
        status = "decrypt_failed"

    return {
        "status": status,
        "mode": client.mode,
        "pairing_id": pairing_id,
        "secret_configured": secret_configured,
        "applied_count": len(applied),
        "applied": applied,
        "skipped": skipped,
        "decrypt_errors": decrypt_errors,
    }

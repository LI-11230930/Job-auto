"""App-first layered notification dispatcher with mobile push hooks and optional email fallback."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from .config import UserConfig, get_project_root
from .db import Database
from .stage3.digest import send_email_digest


def send_mobile_push(
    cfg: UserConfig,
    *,
    title: str,
    body: str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Send optional mobile push notification via Bark / ntfy / ServerChan / PushPlus / Webhook."""
    notif = cfg.notifications
    preset = (notif.push_preset or "none").strip().lower()
    if preset == "none":
        return {"status": "skipped_disabled", "preset": preset}

    root = project_root or get_project_root()
    load_dotenv(root / ".env", override=False)
    env_name = (notif.push_webhook_env or "PUSH_WEBHOOK_URL").strip()
    target_url = os.environ.get(env_name, "").strip()
    if not target_url:
        return {"status": "skipped_missing_push_url", "preset": preset, "env": env_name}

    try:
        with httpx.Client(trust_env=False, timeout=12.0) as client:
            if preset == "bark":
                base = target_url.rstrip("/")
                resp = client.post(
                    f"{base}/{quote(title[:80])}/{quote(body[:500])}",
                    json={"title": title, "body": body, "group": "Job-auto"},
                )
            elif preset == "ntfy":
                resp = client.post(
                    target_url,
                    content=body.encode("utf-8"),
                    headers={"Title": title.encode("ascii", "ignore").decode("ascii") or "Job-auto"},
                )
            elif preset == "serverchan":
                resp = client.post(target_url, data={"title": title, "desp": body})
            elif preset == "pushplus":
                resp = client.post(target_url, json={"title": title, "content": body})
            else:
                resp = client.post(
                    target_url,
                    json={"title": title, "body": body, "text": f"{title}\n{body}", "msgtype": "text"},
                )
            resp.raise_for_status()
            return {"status": "sent", "preset": preset, "http_status": resp.status_code}
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return {"status": "failed", "preset": preset, "error": str(exc)}


def dispatch_notification(
    db: Database,
    cfg: UserConfig,
    *,
    title: str,
    body: str,
    category: str = "daily_digest",
    level: str = "info",
    action_tab: str = "detail",
    payload: dict[str, Any] | None = None,
    email_subject: str | None = None,
    body_text: str | None = None,
    html_body: str | None = None,
    force_email: bool = False,
    email_sender: Any | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Dispatch notifications App-first (in-app inbox + desktop toast + optional mobile push), with email fallback."""
    notif = cfg.notifications
    strategy = (notif.strategy or "app_first").strip().lower()
    delivered: list[str] = []

    app_active = strategy != "email_only" and bool(notif.desktop_notify_enabled)
    if app_active:
        delivered.extend(["app_inbox", "desktop_toast"])

    push_res: dict[str, Any] = {"status": "skipped"}
    if strategy != "email_only" and (notif.push_preset or "none").strip().lower() != "none":
        push_res = send_mobile_push(cfg, title=title, body=body, project_root=project_root)
        if push_res.get("status") == "sent":
            delivered.append(f"mobile_push:{push_res.get('preset')}")

    notification_id: int | None = None
    if app_active or delivered:
        notification_id = db.add_notification(
            title=title,
            body=body,
            level=level,
            category=category,
            action_tab=action_tab,
            payload=payload,
            delivered_channels=delivered,
        )

    should_send_email = False
    email_reason = ""
    if force_email:
        should_send_email = True
        email_reason = "explicit_request"
    elif strategy in {"email_only", "app_and_email"}:
        should_send_email = True
        email_reason = f"strategy:{strategy}"
    elif strategy == "app_first":
        if not delivered:
            should_send_email = True
            email_reason = "fallback_app_unavailable"
        else:
            email_reason = "skipped_app_notified"
    else:
        email_reason = "skipped_app_only"

    if should_send_email:
        sender = email_sender or send_email_digest
        email_res = sender(
            cfg,
            subject=email_subject or f"[Job-auto] {title}",
            body_text=body_text or body,
            html_body=html_body,
        )
        if email_res.get("status") == "sent":
            delivered.append("email_smtp")
            if notification_id is not None:
                db.update_notification_channels(notification_id, delivered)
    else:
        email_res = {
            "status": email_reason,
            "email_to": notif.email_to,
        }

    return {
        "strategy": strategy,
        "notification_id": notification_id,
        "app_notified": "app_inbox" in delivered,
        "delivered_channels": delivered,
        "mobile_push": push_res,
        "email": email_res,
    }

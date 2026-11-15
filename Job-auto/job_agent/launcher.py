"""All-in-one bootstrap, browser+extension discovery, diagnostics, and unified launcher."""

from __future__ import annotations

import os
import platform
import shutil
import sqlite3
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from dotenv import load_dotenv

from .config import get_code_root, get_project_root, load_user_config
from .db import Database


def bootstrap_workspace(
    *,
    root: Path | None = None,
    db_path: Path | None = None,
    copy_examples: bool = True,
) -> dict[str, Any]:
    """Ensure local runtime directories, template configs, and SQLite tables exist."""
    resolved_root = (root or get_project_root()).resolve()
    code_root = get_code_root().resolve()
    for rel in ("data", "output", "local", "logs", "config", "vault"):
        (resolved_root / rel).mkdir(parents=True, exist_ok=True)

    created_files: list[str] = []
    if copy_examples:
        src_base = resolved_root if root is not None else (resolved_root if (resolved_root / ".env.example").exists() else code_root)
        cfg_src_base = resolved_root if root is not None else (resolved_root if (resolved_root / "config" / "user_config.example.yaml").exists() else code_root)
        pairs = [
            (src_base / ".env.example", resolved_root / ".env"),
            (cfg_src_base / "config" / "user_config.example.yaml", resolved_root / "config" / "user_config.yaml"),
        ]
        for src, dst in pairs:
            if not dst.exists() and src.exists():
                shutil.copy2(src, dst)
                created_files.append(str(dst))

    resolved_db = (db_path or (resolved_root / "data" / "job_agent.db")).resolve()
    resolved_db.parent.mkdir(parents=True, exist_ok=True)
    db = Database(resolved_db)
    db.init_schema()

    return {
        "status": "ok",
        "root": str(resolved_root),
        "db_path": str(resolved_db),
        "created_files": created_files,
        "total_jobs": db.count_jobs(),
    }


def resolve_extension_paths(*, root: Path | None = None) -> list[Path]:
    """Discover unpacked MV3 extensions bundled under extensions/ or JOB_AUTO_EXTRA_EXTENSIONS."""
    resolved_root = (root or get_project_root()).resolve()
    code_root = get_code_root().resolve()
    found: list[Path] = []
    seen: set[str] = set()

    bases = (resolved_root,) if root is not None else (resolved_root, code_root)
    for base in bases:
        ext_root = base / "extensions"
        if ext_root.is_dir():
            for child in sorted(ext_root.iterdir()):
                if child.is_dir() and (child / "manifest.json").is_file():
                    key = str(child.resolve()).lower()
                    if key not in seen:
                        seen.add(key)
                        found.append(child.resolve())

    extra_raw = os.getenv("JOB_AUTO_EXTRA_EXTENSIONS", "").strip()
    if extra_raw:
        sep = ";" if os.name == "nt" and ";" in extra_raw else ","
        for part in extra_raw.split(sep):
            cand = Path(part.strip()).expanduser()
            if cand.is_dir() and (cand / "manifest.json").is_file():
                key = str(cand.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(cand.resolve())
    return found


def find_chromium_executable() -> Path | None:
    """Find Microsoft Edge or Google Chrome executable portably across Windows/macOS/Linux."""
    env_override = os.getenv("JOB_AUTO_BROWSER_EXE", "").strip()
    if env_override:
        cand = Path(env_override).expanduser()
        if cand.is_file():
            return cand

    system = platform.system().lower()
    candidates: list[Path] = []

    if system == "windows":
        for env_name in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
            base = os.environ.get(env_name, "").strip()
            if not base:
                continue
            b = Path(base)
            candidates.extend(
                [
                    b / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    b / "Google" / "Chrome" / "Application" / "chrome.exe",
                    b / "Chromium" / "Application" / "chrome.exe",
                ]
            )
        try:
            import winreg

            for subkey in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            ):
                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        with winreg.OpenKey(hive, subkey) as key:
                            val, _ = winreg.QueryValueEx(key, "")
                            if val:
                                candidates.append(Path(str(val)))
                    except OSError:
                        continue
        except ImportError:
            pass
    elif system == "darwin":
        candidates.extend(
            [
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ]
        )
    else:
        for cmd in ("microsoft-edge", "microsoft-edge-stable", "google-chrome", "chromium", "chromium-browser"):
            resolved = shutil.which(cmd)
            if resolved:
                candidates.append(Path(resolved))

    for exe in ("msedge", "chrome", "google-chrome", "chromium"):
        resolved = shutil.which(exe)
        if resolved:
            candidates.append(Path(resolved))

    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def is_http_healthy(url: str, *, timeout: float = 1.2) -> bool:
    try:
        with httpx.Client(trust_env=False, timeout=timeout) as client:
            resp = client.get(url)
            return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def collect_system_status(
    *,
    root: Path | None = None,
    db_path: Path | None = None,
    cdp_url: str = "http://127.0.0.1:9222",
) -> dict[str, Any]:
    """Collect safe readiness diagnostics without exposing any credentials or PII."""
    resolved_root = (root or get_project_root()).resolve()
    load_dotenv(resolved_root / ".env", override=False)
    resolved_db = (db_path or (resolved_root / "data" / "job_agent.db")).resolve()

    env_path = resolved_root / ".env"
    user_cfg_path = resolved_root / "config" / "user_config.yaml"
    cfg = load_user_config()

    gemini_key_set = bool(os.getenv(cfg.llm.api_key_env, "").strip())
    smtp_ready = all(
        bool(os.getenv(env_name, "").strip())
        for env_name in (
            cfg.notifications.smtp_host_env,
            cfg.notifications.smtp_user_env,
            cfg.notifications.smtp_pass_env,
        )
    )

    total_jobs = 0
    active_jobs = 0
    packages_count = 0
    applications_count = 0
    master_loaded = False
    if resolved_db.is_file():
        try:
            db = Database(resolved_db)
            total_jobs = db.count_jobs()
            with db.connect() as conn:
                active_jobs = int(
                    conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'active'").fetchone()[0]
                )
                packages_count = int(conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0])
                applications_count = int(conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0])
                master_loaded = (
                    int(conn.execute("SELECT COUNT(*) FROM master_versions").fetchone()[0]) > 0
                )
        except sqlite3.Error:
            pass

    browser_exe = find_chromium_executable()
    extensions = resolve_extension_paths(root=resolved_root)
    cdp_active = is_http_healthy(f"{cdp_url.rstrip('/')}/json/version", timeout=1.0)

    return {
        "status": "ok",
        "root": str(resolved_root),
        "env_exists": env_path.is_file(),
        "user_config_exists": user_cfg_path.is_file(),
        "db_exists": resolved_db.is_file(),
        "master_loaded": master_loaded,
        "gemini_key_set": gemini_key_set,
        "smtp_ready": smtp_ready,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "packages_count": packages_count,
        "applications_count": applications_count,
        "browser_exe": str(browser_exe) if browser_exe else "",
        "browser_found": browser_exe is not None,
        "extensions": [str(p) for p in extensions],
        "edge_cdp_active": cdp_active,
        "cdp_url": cdp_url,
    }


def launch_cdp_browser(
    *,
    url: str = "http://127.0.0.1:8788/review",
    cdp_port: int = 9222,
    user_data_dir: Path | None = None,
    root: Path | None = None,
    app_mode: bool = False,
) -> dict[str, Any]:
    """Launch Edge/Chrome with remote debugging + bundled collector extension pre-loaded."""
    resolved_root = (root or get_project_root()).resolve()
    cdp_url = f"http://127.0.0.1:{cdp_port}"
    extensions = resolve_extension_paths(root=resolved_root)

    if app_mode:
        browser_exe = find_chromium_executable()
        if browser_exe is None:
            return {
                "ok": False,
                "status": "browser_not_found",
                "error": "未找到 Edge / Chrome 可执行文件",
                "url": url,
            }
        app_profile_dir = (resolved_root / "local" / "app_window_profile").resolve()
        app_profile_dir.mkdir(parents=True, exist_ok=True)
        app_cmd = [
            str(browser_exe),
            f"--user-data-dir={app_profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--app={url}",
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        proc = subprocess.Popen(
            app_cmd,
            cwd=str(resolved_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
        return {
            "ok": True,
            "status": "launched_app_window",
            "pid": proc.pid,
            "browser_exe": str(browser_exe),
            "profile_dir": str(app_profile_dir),
            "url": url,
        }

    if is_http_healthy(f"{cdp_url}/json/version", timeout=1.0):
        opened_tab = False
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url, timeout=3000)
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
                page.bring_to_front()
                opened_tab = True
        except (ImportError, PlaywrightError, OSError):
            opened_tab = False
        return {
            "ok": True,
            "status": "already_running",
            "cdp_url": cdp_url,
            "opened_tab": opened_tab,
            "extensions": [str(p) for p in extensions],
            "url": url,
        }

    browser_exe = find_chromium_executable()
    if browser_exe is None:
        return {
            "ok": False,
            "status": "browser_not_found",
            "error": "未找到 Microsoft Edge 或 Google Chrome，请设置 JOB_AUTO_BROWSER_EXE 或手动打开浏览器访问工作台。",
            "url": url,
        }

    profile_dir = (user_data_dir or (resolved_root / "local" / "edge_profile")).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(browser_exe),
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if extensions:
        cmd.append(f"--load-extension={','.join(str(p) for p in extensions)}")
    cmd.append(f"--app={url}" if app_mode else url)

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )

    proc = subprocess.Popen(
        cmd,
        cwd=str(resolved_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
    )
    return {
        "ok": True,
        "status": "launched",
        "pid": proc.pid,
        "browser_exe": str(browser_exe),
        "cdp_url": cdp_url,
        "profile_dir": str(profile_dir),
        "extensions": [str(p) for p in extensions],
        "url": url,
    }


def _open_when_ready(
    *,
    health_url: str,
    target_url: str,
    cdp_port: int,
    launch_cdp: bool,
    root: Path,
    app_mode: bool = False,
) -> None:
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        if is_http_healthy(health_url, timeout=0.8):
            if launch_cdp:
                res = launch_cdp_browser(
                    url=target_url,
                    cdp_port=cdp_port,
                    root=root,
                    app_mode=app_mode,
                )
                if res.get("ok"):
                    return
            webbrowser.open(target_url)
            return
        time.sleep(0.25)


def run_unified_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8788,
    db_path: Path | None = None,
    cdp_port: int = 9222,
    open_browser: bool = True,
    launch_cdp: bool = True,
    app_mode: bool = False,
) -> int:
    """Bootstrap workspace + launch unified Workbench/Extension server + open browser."""
    from .progress import update_progress_artifacts
    from .stage3.review_server import create_review_app

    root = get_project_root()
    boot = bootstrap_workspace(root=root, db_path=db_path, copy_examples=True)
    resolved_db = Path(boot["db_path"])
    load_dotenv(root / ".env", override=False)

    try:
        if resolved_db == (root / "data" / "job_agent.db").resolve():
            update_progress_artifacts(db_path=resolved_db)
    except (OSError, ValueError):
        pass

    health_url = f"http://{host}:{port}/health"
    target_url = f"http://{host}:{port}/review"

    if is_http_healthy(health_url, timeout=1.0):
        print(f"[Job-auto] 统一工作台与插件接收器已在运行：{target_url}")
        if open_browser:
            if launch_cdp:
                res = launch_cdp_browser(
                    url=target_url,
                    cdp_port=cdp_port,
                    root=root,
                    app_mode=app_mode,
                )
                if not res.get("ok"):
                    webbrowser.open(target_url)
            else:
                webbrowser.open(target_url)
        return 0

    if open_browser:
        threading.Thread(
            target=_open_when_ready,
            kwargs={
                "health_url": health_url,
                "target_url": target_url,
                "cdp_port": cdp_port,
                "launch_cdp": launch_cdp,
                "root": root,
                "app_mode": app_mode,
            },
            daemon=True,
        ).start()

    print("========================================================")
    print("  Job-auto 一键统一服务已启动（工作台 + 浏览器扩展同端口）")
    print(f"  - 审核与控制中心：{target_url}")
    print(f"  - 项目进度看板：  http://{host}:{port}/progress")
    print(f"  - 浏览器扩展接口：http://{host}:{port}/api/inbox/health")
    print("========================================================")

    app = create_review_app(db_path=resolved_db)
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0

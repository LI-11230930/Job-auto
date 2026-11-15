"""Build standalone PyInstaller sidecar executable (`job-agent-backend.exe`) for Electron."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    desktop_dir = Path(__file__).resolve().parent
    repo_root = desktop_dir.parent
    entry = repo_root / "Job-auto" / "job_agent" / "sidecar_main.py"
    dist_dir = desktop_dir / "backend-bin"
    work_dir = desktop_dir / "build-pyinstaller"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)

    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        "job-agent-backend",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        "--paths",
        str(repo_root / "Job-auto"),
        "--collect-submodules",
        "job_agent",
        "--collect-submodules",
        "uvicorn",
        "--collect-submodules",
        "fastapi",
        "--collect-submodules",
        "starlette",
        "--collect-submodules",
        "pydantic",
        "--collect-submodules",
        "google.genai",
        "--collect-submodules",
        "cryptography",
        "--collect-data",
        "certifi",
        "--collect-data",
        "playwright",
        "--hidden-import",
        "playwright.sync_api",
        "--hidden-import",
        "playwright.async_api",
        "--hidden-import",
        "pypdf",
        "--hidden-import",
        "yaml",
        "--hidden-import",
        "dotenv",
        "--hidden-import",
        "httpx",
        "--hidden-import",
        "PIL",
        "--add-data",
        f"{repo_root / 'prompts'}{sep}prompts",
        "--add-data",
        f"{repo_root / 'config' / 'user_config.example.yaml'}{sep}config",
        "--add-data",
        f"{repo_root / 'config' / 'extensions.example.yaml'}{sep}config",
        str(entry),
    ]
    print("[build_backend] Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(repo_root), check=True)
    exe_name = "job-agent-backend.exe" if os.name == "nt" else "job-agent-backend"
    built_exe = dist_dir / "job-agent-backend" / exe_name
    if not built_exe.is_file():
        raise FileNotFoundError(f"Expected bundled backend not found: {built_exe}")
    print("[build_backend] Ready:", built_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "[Job-auto] 首次运行：正在创建 .venv 并安装依赖..."
  python3 -m venv .venv
  .venv/bin/python -m pip install -U pip
  .venv/bin/python -m pip install -e .
fi

echo "[Job-auto] 正在启动统一工作台 + 扩展接收器 + 带插件浏览器..."
exec .venv/bin/python -m job_agent.cli up "$@"

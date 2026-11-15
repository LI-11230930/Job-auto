"""Frozen-executable entrypoint for Job-auto desktop sidecar & CLI."""

from __future__ import annotations

import multiprocessing


def _run() -> int:
    multiprocessing.freeze_support()
    from job_agent.cli import main

    return int(main() or 0)


if __name__ == "__main__":
    raise SystemExit(_run())

"""Unit tests for SQLite schema initialization and deduplicated upsert."""

from __future__ import annotations

import json
from pathlib import Path

from job_agent.db import Database
from job_agent.sources.base import CHANNEL_PRIORITY, compute_dedup_hash


def test_init_schema_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.init_schema()

    with db.connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert {
        "master_versions",
        "jobs",
        "matches",
        "packages",
        "decisions",
        "applications",
        "runs",
    }.issubset(tables)
    assert str(journal_mode).lower() == "wal"


def test_upsert_merges_cities_and_prefers_higher_channel(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.init_schema()

    dedup = compute_dedup_hash(company="示例集团", title="财务管培生", job_type="校招")
    first = {
        "source": "campus_site:givemeoc",
        "source_job_id": "g-1",
        "company": "示例集团",
        "title": "财务管培生",
        "cities": ["上海"],
        "job_type": "校招",
        "jd_text": "财务轮岗",
        "url": "https://www.givemeoc.com/job/1",
        "apply_channel": "third_party",
        "apply_target": "https://www.givemeoc.com/job/1",
        "deadline": "",
        "industry": "消费品",
        "status": "active",
        "dedup_hash": dedup,
        "priority_rank": CHANNEL_PRIORITY["third_party"],
    }
    res1 = db.upsert_jobs([first])
    assert res1 == {"inserted": 1, "updated": 0, "skipped": 0}

    second = {
        **first,
        "source": "campus_site:company_careers",
        "cities": ["北京", "上海"],
        "url": "https://careers.example.com/finance",
        "apply_channel": "company_portal",
        "apply_target": "https://careers.example.com/finance",
        "priority_rank": CHANNEL_PRIORITY["company_portal"],
    }
    res2 = db.upsert_jobs([second])
    assert res2 == {"inserted": 0, "updated": 1, "skipped": 0}
    assert db.count_jobs() == 1

    with db.connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE dedup_hash = ?", (dedup,)).fetchone()
    assert row["apply_channel"] == "company_portal"
    assert json.loads(row["cities_json"]) == ["上海", "北京"]

    # Idempotent re-import skips unchanged record
    res3 = db.upsert_jobs([second])
    assert res3 == {"inserted": 0, "updated": 0, "skipped": 1}
